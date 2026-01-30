# regWM.py
import torch
from server import register_internal, register_external_builder, model, tokenizer, vocab_ids

# 示例A：把 HF 的 WatermarkLogitsProcessor 当作“内置”
# from transformers import WatermarkLogitsProcessor
# greenlist = WatermarkLogitsProcessor(
#     vocab_size=max(vocab_ids)+1,  # 或直接 tokenizer.vocab_size
#     device="cuda",                # 按需
#     greenlist_ratio=0.25,
#     bias=2.0,
#     hashing_key=123456789,
#     seeding_scheme="lefthash",
#     context_width=2,
# )
# register_internal("greenlist_default", greenlist)

# 示例B：你的自定义处理器，当作“外置”
from libWM.wllm import WLLMLogitsProcessor as WLLM
from libWM.sweet import SWEETLogitsProcessor as Sweet
from libWM.waterfall import WaterfallLogitsProcessor as Waterfall
from libWM.stone import STONEWMLogitsProcessor as Stone
from libWM.ewd import EWDWMLogitsProcessor as EWD
from libWM.codeip.codeipLP import CodeipLogitsProcessor as Codeip

# ===== 纯 builder 化：仅注册可参数化 builder =====
def build_wllm(**cfg):
    gamma = cfg.get("gamma", 0.5)
    delta = cfg.get("delta", 1)
    z_threshold = cfg.get("z_threshold", 4.0)
    ignore_repeated_bigrams = cfg.get("ignore_repeated_bigrams", False)
    # vocab 由服务端注入 vocab_ids，这里不从 cfg 读取
    return WLLM(
        vocab=vocab_ids, 
        gamma=gamma, 
        delta=delta,
        tokenizer=tokenizer,
        z_threshold=float(z_threshold),
        ignore_repeated_bigrams = bool(ignore_repeated_bigrams),
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
        tokenizer=tokenizer,  # 便于 detect_from_text 使用；纯 token id 检测不强制
        z_threshold=z_threshold,
        ignore_repeated_bigrams=bool(ignore_repeated_bigrams),
    )

# 例：若你的环境提供 tokenizer，可不传 vocab_ids/N
# 若仅有 vocab_ids，且是 0..N-1 稠密区间，也可只传 vocab_ids
# 若 vocab_ids 非稠密，请显式传 N=模型词表大小

def build_waterfall(**cfg):
    """
    cfg 可用字段：
      id_mu(int), k_p(int), kappa(float), n_gram(int=2), wm_fn(str="fourier"),
      # N 的确定（传其一即可，优先级：tokenizer > 稠密 vocab_ids）
      tokenizer=None, vocab_ids=None,
      # 动态批检测（默认 'batch'；如有动态合批/拆分，建议 'row_any'）
      auto_reset(bool)=True, detect_mode(str)="batch"  # or "row_any"
    """
    # 先从 cfg 中读取并保存到局部变量
    id_mu = int(cfg.get("id_mu", 42))
    k_p = int(cfg.get("k_p", 1))
    kappa = float(cfg.get("kappa", 2.0))
    n_gram = int(cfg.get("n_gram", 2))
    wm_fn = str(cfg.get("wm_fn", "fourier"))
    auto_reset = bool(cfg.get("auto_reset", True))
    detect_mode = str(cfg.get("detect_mode", "batch"))

    # 使用上述变量进行构造
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
    # 单卡/常规加载：model.device 就够用
    dev = getattr(model, "device", None)
    if dev is not None and dev != torch.device("meta"):
        return dev
    # 兜底：从参数推断
    try:
        return next(model.parameters()).device
    except StopIteration:
        # 极少数场景（比如刚构建还没init参数）
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

def infer_vocab_size(tokenizer, model) -> int:
    # 首选 tokenizer.vocab_size（和 HF 生态最对齐）
    if hasattr(tokenizer, "vocab_size") and tokenizer.vocab_size:
        return int(tokenizer.vocab_size)
    # 其次看模型 config
    if hasattr(model, "config") and hasattr(model.config, "vocab_size"):
        return int(model.config.vocab_size)
    # 再兜底看输出层
    out_emb = getattr(model, "get_output_embeddings", lambda: None)()
    if out_emb is not None and hasattr(out_emb, "num_embeddings"):
        return int(out_emb.num_embeddings)
    raise ValueError("无法推断 vocab_size：请手动传入或检查 tokenizer/model 是否已就绪")

def build_ewd(**cfg):
    # 先从 cfg / 现有上下文读取并保存到局部变量
    vocab_size   = infer_vocab_size(tokenizer, model)
    device       = infer_device(model)
    gamma        = float(cfg.get("gamma", 0.5))
    delta        = float(cfg.get("delta", 2.0))
    hash_key     = int(cfg.get("hash_key", 15485863))
    z_threshold  = float(cfg.get("z_threshold", 4.0))
    prefix_length= int(cfg.get("prefix_length", 1))
    gen_kwargs   = cfg.get("gen_kwargs") or {}

    # 使用上述变量进行构造
    return EWD(
        tokenizer=tokenizer,
        model=model,               # EWD 的零参检测需要用到模型计算熵
        device=device,
        vocab_size=vocab_size,
        gamma=gamma,
        delta=delta,
        hash_key=hash_key,
        z_threshold=z_threshold,
        prefix_length=prefix_length,
    )

def build_stone(**cfg):
    # 先从 cfg 中读取并保存到局部变量
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

    # 使用上述变量进行构造
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

        # infer tokenizer from outer context; regWM file provides `tokenizer` variable
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