from __future__ import annotations
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Iterable, Optional

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|==|!=|\+\+|--|&&|\|\||[0-9]+")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


@dataclass
class RuleCard:
    id: str
    channel: str
    languages: List[str]
    title: str
    description: str
    preconditions: List[str]
    example: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RuleCard":
        return cls(**d)

    def document(self) -> str:
        return " ".join([self.id, self.channel, self.title, self.description,
                         " ".join(self.preconditions), self.example])

    def prompt_block(self) -> str:
        pres = "; ".join(self.preconditions)
        return (f"RULE_ID: {self.id}\nCHANNEL: {self.channel}\nTITLE: {self.title}\n"
                f"DESCRIPTION: {self.description}\nPRECONDITIONS: {pres}\nEXAMPLE: {self.example}")


class BM25RuleRetriever:
    """Small deterministic BM25 retriever over the hard-rule knowledge base.

    This is intentionally local and dependency-free so the RAG configuration can be
    archived and reproduced exactly. It is RAG over transformation rule cards, not a
    claim of semantic search over an external corpus.
    """
    def __init__(self, rules: Iterable[RuleCard], k1: float = 1.5, b: float = 0.75):
        self.rules = list(rules)
        self.k1 = k1
        self.b = b
        self.docs = [tokenize(r.document()) for r in self.rules]
        self.avgdl = sum(map(len, self.docs)) / max(1, len(self.docs))
        self.df: Dict[str, int] = {}
        for doc in self.docs:
            for tok in set(doc):
                self.df[tok] = self.df.get(tok, 0) + 1

    @classmethod
    def from_json(cls, path: str | Path) -> "BM25RuleRetriever":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(RuleCard.from_dict(x) for x in data)

    def _score(self, query_tokens: List[str], idx: int) -> float:
        doc = self.docs[idx]
        if not doc:
            return 0.0
        tf: Dict[str, int] = {}
        for t in doc:
            tf[t] = tf.get(t, 0) + 1
        n = len(self.docs)
        score = 0.0
        for q in query_tokens:
            fq = tf.get(q, 0)
            if fq == 0:
                continue
            df = self.df.get(q, 0)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            denom = fq + self.k1 * (1 - self.b + self.b * len(doc) / max(self.avgdl, 1e-9))
            score += idf * (fq * (self.k1 + 1)) / denom
        return score

    def retrieve(self, query: str, language: str, channel: str, top_k: int = 4) -> List[RuleCard]:
        q = tokenize(query)
        candidates = []
        for i, rule in enumerate(self.rules):
            if language not in rule.languages:
                continue
            if channel != "all" and rule.channel != channel:
                continue
            # Channel match receives a deterministic prior to avoid irrelevant rules on short code.
            prior = 2.0 if (channel == "all" or rule.channel == channel) else 0.0
            candidates.append((self._score(q, i) + prior, rule.id, rule))
        candidates.sort(key=lambda x: (-x[0], x[1]))
        if channel != "all":
            return [r for _, _, r in candidates[:top_k]]
        # ALL: ensure channel diversity before filling remaining slots.
        selected: List[RuleCard] = []
        seen = set()
        for ch in ("id", "expr", "block"):
            for _, _, r in candidates:
                if r.channel == ch:
                    selected.append(r); seen.add(r.id); break
        for _, _, r in candidates:
            if len(selected) >= top_k:
                break
            if r.id not in seen:
                selected.append(r); seen.add(r.id)
        return selected[:top_k]
