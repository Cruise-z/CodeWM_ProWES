# regWM.py
import torch
from processors import register_internal, register_external_builder
from runtime import model, tokenizer, vocab_ids

# Example A: treat HF's WatermarkLogitsProcessor as an "internal" processor
# from transformers import WatermarkLogitsProcessor
# greenlist = WatermarkLogitsProcessor(
#     vocab_size=max(vocab_ids)+1,  # or just tokenizer.vocab_size
#     device="cuda",                # as needed
#     greenlist_ratio=0.25,
#     bias=2.0,
#     hashing_key=123456789,
#     seeding_scheme="lefthash",
#     context_width=2,
# )
# register_internal("greenlist_default", greenlist)

# Example B: your custom processors, treated as "external"
from libWM.wllm import WLLMLogitsProcessor as WLLM
from libWM.sweet import SWEETLogitsProcessor as Sweet
from libWM.waterfall import WaterfallLogitsProcessor as Waterfall
from libWM.stone import STONEWMLogitsProcessor as Stone
from libWM.ewd import EWDWMLogitsProcessor as EWD
from libWM.codeip.codeipLP import CodeipLogitsProcessor as Codeip

# ===== Builder-only: register parameterizable builders only =====
def build_wllm(**cfg):
    gamma = cfg.get("gamma", 0.5)
    delta = cfg.get("delta", 1)
    z_threshold = cfg.get("z_threshold", 4.0)
    ignore_repeated_bigrams = cfg.get("ignore_repeated_bigrams", False)
    # vocab is injected by the server via vocab_ids; do not read it from cfg here
    return WLLM(
        vocab=vocab_ids,
        gamma=gamma,
        delta=delta,
        tokenizer=tokenizer,
        z_threshold=float(z_threshold),
        ignore_repeated_bigrams=bool(ignore_repeated_bigrams),
    )

def build_sweet(**cfg):
    gamma = cfg.get("gamma", 0.5)
    delta = cfg.get("delta", 1)
    entropy_threshold = cfg.get("entropy_threshold", 0.9)
    z_threshold = cfg.get("z_threshold", 4.0)
    ignore_repeated_bigrams = cfg.get("ignore_repeated_bigrams", False)
    return Sweet(
        vocab=vocab_ids,
        gamma=gamma,
        delta=delta,
        entropy_threshold=entropy_threshold,
        tokenizer=tokenizer,  # convenient for detect_from_text; token-id-only detection doesn't require it
        z_threshold=z_threshold,
        ignore_repeated_bigrams=bool(ignore_repeated_bigrams),
    )

# Note: if your environment provides tokenizer, you can skip passing vocab_ids/N.
# If you only have vocab_ids and it is a dense range 0..N-1, you can pass just vocab_ids.
# If vocab_ids is not dense, explicitly pass N=the model vocab size.

def build_waterfall(**cfg):
    """
    Available cfg fields:
      id_mu(int), k_p(int), kappa(float), n_gram(int=2), wm_fn(str="fourier"),
      # How to determine N (pass one; priority: tokenizer > dense vocab_ids)
      tokenizer=None, vocab_ids=None,
      # Dynamic batch detection (default 'batch'; if you have dynamic micro-batching/splitting, recommend 'row_any')
      auto_reset(bool)=True, detect_mode(str)="batch"  # or "row_any"
    """
    # Read from cfg and store in local variables first
    id_mu = int(cfg.get("id_mu", 42))
    k_p = int(cfg.get("k_p", 1))
    kappa = float(cfg.get("kappa", 2.0))
    n_gram = int(cfg.get("n_gram", 2))
    wm_fn = str(cfg.get("wm_fn", "fourier"))
    auto_reset = bool(cfg.get("auto_reset", True))
    detect_mode = str(cfg.get("detect_mode", "batch"))

    # Construct using the variables above
    return Waterfall(
        tokenizer=tokenizer,
        vocab_ids=vocab_ids,
        id_mu=id_mu,
        k_p=k_p,
        kappa=kappa,
        n_gram=n_gram,
        wm_fn=wm_fn,
        det_tokenizer=tokenizer,
        auto_reset=auto_reset,
        detect_mode=detect_mode,
    )

def infer_device(model) -> torch.device:
    # Single-GPU / typical loading: model.device is enough
    dev = getattr(model, "device", None)
    if dev is not None and dev != torch.device("meta"):
        return dev
    # Fallback: infer from parameters
    try:
        return next(model.parameters()).device
    except StopIteration:
        # Rare cases (e.g., just constructed and parameters not initialized yet)
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

def infer_vocab_size(tokenizer, model) -> int:
    # Prefer tokenizer.vocab_size (most aligned with HF ecosystem)
    if hasattr(tokenizer, "vocab_size") and tokenizer.vocab_size:
        return int(tokenizer.vocab_size)
    # Next: model config
    if hasattr(model, "config") and hasattr(model.config, "vocab_size"):
        return int(model.config.vocab_size)
    # Last resort: output embeddings
    out_emb = getattr(model, "get_output_embeddings", lambda: None)()
    if out_emb is not None and hasattr(out_emb, "num_embeddings"):
        return int(out_emb.num_embeddings)
    raise ValueError("Unable to infer VOCAB_Size: Please manually input or check if tokenizer/model is ready")

def build_ewd(**cfg):
    # Read from cfg / current context and store in local variables first
    vocab_size   = infer_vocab_size(tokenizer, model)
    device       = infer_device(model)
    gamma        = float(cfg.get("gamma", 0.5))
    delta        = float(cfg.get("delta", 2.0))
    hash_key     = int(cfg.get("hash_key", 15485863))
    z_threshold  = float(cfg.get("z_threshold", 4.0))
    prefix_length= int(cfg.get("prefix_length", 1))
    gen_kwargs   = cfg.get("gen_kwargs") or {}

    # Construct using the variables above
    return EWD(
        tokenizer=tokenizer,
        model=model,               # EWD's zero-parameter detection needs the model to compute entropy
        device=device,
        vocab_size=vocab_size,
        gamma=gamma,
        delta=delta,
        hash_key=hash_key,
        z_threshold=z_threshold,
        prefix_length=prefix_length,
    )

def build_stone(**cfg):
    # Read from cfg and store in local variables first
    vocab_size = infer_vocab_size(tokenizer, model)
    device     = infer_device(model)
    gamma          = float(cfg.get("gamma", 0.5))
    delta          = float(cfg.get("delta", 2.0))
    hash_key       = int(cfg.get("hash_key", 15485863))
    z_threshold    = float(cfg.get("z_threshold", 4.0))
    prefix_length  = int(cfg.get("prefix_length", 1))
    language       = str(cfg.get("language", "java"))
    watermark_on_pl = str(cfg.get("watermark_on_pl", "False"))
    skipping_rule  = cfg.get("skipping_rule", "all_pl")

    # Construct using the variables above
    return Stone(
        tokenizer=tokenizer,
        vocab_size=vocab_size,
        device=device,
        gamma=gamma,
        delta=delta,
        hash_key=hash_key,
        z_threshold=z_threshold,
        prefix_length=prefix_length,
        language=language,
        watermark_on_pl=watermark_on_pl,
        skipping_rule=skipping_rule,
    )
    
def build_codeip(**cfg):
        """
        Builder for the codeip watermark processor wrapper.

        Expected cfg keys (best-effort, many optional since regWM/context may provide tokenizer/model):
            - mode: 'random' or 'pda'
            - delta, gamma, message_code_len, encode_ratio, top_k
            - pda_model (if mode=='pda')
            - device
            - message (list[int])
        """
        mode = str(cfg.get("mode", "random"))
        device = infer_device(model)
        delta = float(cfg.get("delta", 5.0))
        gamma = float(cfg.get("gamma", 3.0))
        message_code_len = int(cfg.get("message_code_len", 20))
        encode_ratio = float(cfg.get("encode_ratio", 10.0))
        top_k = int(cfg.get("top_k", 1000))
        message = cfg.get("message", [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1])
        pda_model = cfg.get("pda_model", None)

        # Infer tokenizer from outer context; regWM file provides the `tokenizer` variable
        return Codeip(
                processor=None,
                mode=mode,
                tokenizer=tokenizer,
                lm_tokenizer=tokenizer,
                pda_model=pda_model,
                message=message,
                delta=delta,
                message_code_len=message_code_len,
                encode_ratio=encode_ratio,
                top_k=top_k,
                gamma=gamma,
                device=device,
        )


register_external_builder("wllm", build_wllm)
register_external_builder("sweet", build_sweet)
register_external_builder("waterfall", build_waterfall)
register_external_builder("ewd", build_ewd)
register_external_builder("stone", build_stone)
register_external_builder("codeip", build_codeip)
