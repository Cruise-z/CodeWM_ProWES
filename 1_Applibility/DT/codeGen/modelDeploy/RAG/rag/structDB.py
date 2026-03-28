# pip install faiss-cpu torch transformers numpy rapidfuzz
import json
from pathlib import Path
import numpy as np
import torch
import faiss
from transformers import AutoTokenizer, AutoModel
from rapidfuzz import fuzz, process
import os
work_space = Path(__file__).resolve().parent
os.chdir(work_space)

# ========= Replaceable embedding model =========
# Strong general retrieval: intfloat/e5-base-v2 (recommended)
# For code retrieval: microsoft/codebert-base or
# jinaai/jina-embeddings-v2-base-code
EMBED_MODEL_NAME = "intfloat/e5-base-v2"

tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_NAME)
encoder = AutoModel.from_pretrained(EMBED_MODEL_NAME)

def _prefix_for_e5(text, is_query: bool):
    # Prefixes are recommended for the E5 family
    if "intfloat/e5" in EMBED_MODEL_NAME:
        return f"{'query' if is_query else 'passage'}: {text}"
    return text

@torch.no_grad()
def encode_batch(texts, is_query=False, batch_size=16, max_length=512):
    """Mean pooling + L2 normalization (for cosine similarity / inner-product retrieval)."""
    out_list = []
    for i in range(0, len(texts), batch_size):
        batch = [_prefix_for_e5(t, is_query) for t in texts[i:i+batch_size]]
        inputs = tokenizer(batch, return_tensors="pt", truncation=True, padding=True, max_length=max_length)
        outputs = encoder(**inputs).last_hidden_state  # [B, L, H]
        mask = inputs["attention_mask"].unsqueeze(-1) # [B, L, 1]
        masked = outputs * mask
        mean_emb = masked.sum(dim=1) / mask.sum(dim=1).clamp(min=1)  # [B, H]
        vecs = mean_emb.cpu().numpy().astype("float32")
        # Normalize so inner product equals cosine similarity
        faiss.normalize_L2(vecs)
        out_list.append(vecs)
    return np.vstack(out_list)

def load_jsonl(jsonl_path):
    rows = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            obj = json.loads(line)
            ref = obj.get("reference") or ""
            if not ref:
                continue
            rows.append({
                "task_id": obj.get("task_id", i),
                "task_name": obj.get("task_name", ""),
                "prompt": obj.get("prompt", ""),
                "prefix": obj.get("prefix", ""),
                "reference": ref
            })
    return rows

def make_passage_text(r):
    """Build the indexed text by including task_name/prompt/prefix/reference snippets to improve retrievability."""
    ref_head = r["reference"][:2000]   # Truncate according to length as needed
    pre_head = r["prefix"][:1000]
    prm_head = r["prompt"][:1000]
    parts = [
        f"[task_name] {r['task_name']}",
        f"[prompt] {prm_head}",
        f"[prefix] {pre_head}",
        f"[reference_head] {ref_head}"
    ]
    return "\n".join(parts)

def build_knowledge_base(
    jsonl_path,
    index_path="./knowledge_base.index",
    meta_path="./knowledge_meta.json"
):
    data = load_jsonl(jsonl_path)
    if not data:
        raise ValueError("No usable records were found in the JSONL file (missing reference field).")

    passages = [make_passage_text(r) for r in data]
    vecs = encode_batch(passages, is_query=False)  # passage vectors

    dim = vecs.shape[1]
    index = faiss.IndexFlatIP(dim)      # cosine similarity (vectors are already L2-normalized)
    index.add(vecs)
    faiss.write_index(index, index_path)

    meta = {
        "embed_model": EMBED_MODEL_NAME,
        "count": len(data),
        "rows": data
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"*Index: {Path(index_path).resolve()}")
    print(f"*Metadata: {Path(meta_path).resolve()}")
    print(f"*Document count: {len(data)}")

def _load_kb(index_path, meta_path):
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return index, meta

def _combine_text(prompt: str, prefix: str, max_len_prompt=2000, max_len_prefix=2000):
    p = (prompt or "")[:max_len_prompt]
    pre = (prefix or "")[:max_len_prefix]
    return (p + "\n" + pre).strip()

def retrieve_reference(
    query_text: str,
    top_k: int = 1,
    index_path: str = "./knowledge_base.index",
    meta_path: str = "./knowledge_meta.json",
    prefer_exact: bool = True,
    fuzzy_task_threshold: int = 85,
    fuzzy_pp_threshold: int = 80,
    vector_fallback: bool = True
):
    """
    Multi-route retrieval merge:
      1) exact containment match on task_name (highest priority)
      2) fuzzy match on task_name (WRatio)
      3) fuzzy match on (prompt + prefix) (WRatio)
      4) if fewer than top_k are found above, fall back to vector retrieval (cosine)
    Returns: [{rank, score, task_id, task_name, prompt, prefix, reference, route}, ...]
    """
    index, meta = _load_kb(index_path, meta_path)
    rows = meta["rows"]

    # ---------- 1) Exact containment on task_name ----------
    ql = (query_text or "").lower().strip()
    if prefer_exact and ql:
        exact_hits = [i for i, r in enumerate(rows) if ql in (r.get("task_name") or "").lower()]
        if exact_hits:
            i = exact_hits[0]
            r = rows[i]
            return [{
                "rank": 1,
                "score": 1.0,
                "task_id": r["task_id"],
                "task_name": r.get("task_name", ""),
                "prompt": r.get("prompt", ""),
                "prefix": r.get("prefix", ""),
                "reference": r.get("reference", ""),
                "route": "task_name_exact"
            }]

    # First collect candidates from multiple routes and keep the highest score on dedup
    cand = {}  # fid -> (score, route)

    # ---------- 2) Fuzzy task_name match ----------
    task_choices = [((r.get("task_name") or ""), i) for i, r in enumerate(rows)]
    if task_choices:
        # Take the top candidate set to improve recall; you can also change
        # limit to len(rows) to score everything
        task_top = process.extract(
            query_text, task_choices, scorer=fuzz.WRatio, limit=min(20, len(task_choices))
        )
        for (matched_text, i, score) in task_top:
            if score >= fuzzy_task_threshold:
                prev = cand.get(i)
                if (prev is None) or (score/100.0 > prev[0]):
                    cand[i] = (score/100.0, "task_name_fuzzy")

    # ---------- 3) Fuzzy (prompt + prefix) match ----------
    pp_choices = []
    for i, r in enumerate(rows):
        pp = _combine_text(r.get("prompt", ""), r.get("prefix", ""))
        pp_choices.append((pp, i))
    if pp_choices:
        pp_top = process.extract(
            query_text, pp_choices, scorer=fuzz.WRatio, limit=min(50, len(pp_choices))
        )
        for (matched_text, i, score) in pp_top:
            if score >= fuzzy_pp_threshold:
                prev = cand.get(i)
                if (prev is None) or (score/100.0 > prev[0]):
                    cand[i] = (score/100.0, "pp_fuzzy")

    # Sort fuzzy candidates by score and keep top_k
    fuzzy_results = sorted(cand.items(), key=lambda kv: kv[1][0], reverse=True)
    results = []
    for rank, (fid, (sc, route)) in enumerate(fuzzy_results[:top_k], 1):
        r = rows[fid]
        results.append({
            "rank": rank,
            "score": float(sc),
            "task_id": r["task_id"],
            "task_name": r.get("task_name", ""),
            "prompt": r.get("prompt", ""),
            "prefix": r.get("prefix", ""),
            "reference": r.get("reference", ""),
            "route": route
        })

    # ---------- 4) Vector fallback ----------
    if vector_fallback and len(results) < top_k:
        need = top_k - len(results)
        # Use query_text directly for vector retrieval
        # (this can also be changed to prompt+prefix concatenation)
        from numpy import unique
        q_vec = encode_batch([query_text], is_query=True)  # Reuse the encode_batch defined above
        scores, idx = index.search(q_vec, need * 2)        # Over-fetch to avoid overlap with fuzzy candidates
        used_fids = set([rows.index(res) if isinstance(res, dict) else res for res in []])  # Compatibility reminder

        used = set([int(rows.index(r)) for r in []])  # Unused line, only kept to avoid error-report confusion; can be ignored
        picked = 0
        for sc, fid in zip(scores[0], idx[0]):
            if fid < 0:  # FAISS may return -1
                continue
            if int(fid) in cand:  # Avoid duplicates with fuzzy candidates
                continue
            r = rows[int(fid)]
            results.append({
                "rank": len(results) + 1,
                "score": float(sc),
                "task_id": r["task_id"],
                "task_name": r.get("task_name", ""),
                "prompt": r.get("prompt", ""),
                "prefix": r.get("prefix", ""),
                "reference": r.get("reference", ""),
                "route": "vector"
            })
            picked += 1
            if picked >= need:
                break

    # Keep only top_k in the final result
    return results[:top_k]

# ===== Usage example =====
# Build/rebuild the index first (only needed once)
build_knowledge_base("./projectDev_java.jsonl")

# Query
query = "snake game"
hits = retrieve_reference(query, top_k=1)
for h in hits:
    print(h["rank"], h["route"], h["task_name"], h["score"])
    print(h["reference"])
