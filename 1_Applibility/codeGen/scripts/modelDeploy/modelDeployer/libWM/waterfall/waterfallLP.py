# waterfallLP.py
# 仅封装 logits processor，对齐官方实现：
# - 复用官方 PerturbationProcessor 与 WatermarkingFn*(生成同一 φ)
# - 采样链顺序仍由你在外部控制（采样 warper 在前，waterfall 在后）
# - 将“检出(verify)”能力归入处理器类，保持原嵌入逻辑不变
import numpy as np
from typing import Iterable, Optional, List, Union, Dict, Any, cast
import torch
import time as _time
from transformers.generation.logits_process import LogitsProcessor

from .WatermarkerBase import PerturbationProcessor, Watermarker
from .WatermarkingFnFourier import WatermarkingFnFourier
from .WatermarkingFnSquare import WatermarkingFnSquare


def _resolve_vocab_size(
    tokenizer=None,
    vocab_ids: Optional[Iterable[int]] = None,
) -> int:
    """
    统一确定 N (和官方一致：scores[:, :N] 上加扰)
    优先级：tokenizer.vocab_size > 稠密的 vocab_ids
    若 vocab_ids 非 0..N-1 的稠密区间，必须显式传tokenizer。
    """
    if tokenizer is not None and getattr(tokenizer, "vocab_size", None) is not None:
        return int(tokenizer.vocab_size)

    if vocab_ids is not None:
        ids = list(vocab_ids)
        if not ids:
            raise ValueError("vocab_ids为空; 请显式传tokenizer")
        mn, mx = min(ids), max(ids)
        # 稠密性检查: 必须是 [0, 1, ..., mx] 且 mn == 0 且 无缺口
        if mn == 0 and len(set(ids)) == (mx + 1):
            return mx + 1
        raise ValueError(
            "检测到非稠密 vocab_ids (不是从 0 到 N-1 的连续区间)"
            "请显式传 tokenizer(N=tokenizer.vocab_size), 以与官方实现完全对齐"
        )

    raise ValueError("无法确定 N; 请传入 tokenizer 或稠密的 vocab_ids")


class WaterfallLogitsProcessor(LogitsProcessor):
    """
    - 生成 φ（Fourier/Square）→ 注入官方 PerturbationProcessor
    - 内置 auto-reset：检测“新一轮生成开始”并自动 reset(n_gram)
      * 默认按批检测（batch 级别）；也提供逐行检测并在发现任意样本重启时对整批 reset，
        以确保不会漏掉任何新序列（官方是批级 reset）。
    - 离线检出能力（零参）：detect_last()
      * 处理器在 __call__ 内持续缓存“本轮新增的 continuation token”（不含提示词），
        服务端在生成结束后可直接零参调用检测。
    """

    def __init__(
        self,
        *,
        id_mu: int,
        k_p: int,
        kappa: float,
        n_gram: int = 2,
        wm_fn: str = "fourier",
        # 下面2个参数用于确定N(优先级见 _resolve_vocab_size)
        tokenizer=None,
        vocab_ids: Optional[Iterable[int]] = None,
        # 动态批控制
        auto_reset: bool = True,
        detect_mode: str = "batch",  # "batch" | "row_any"
        # 检出依赖（用于 Watermarker.verify 的分词）
        det_tokenizer=None,          # 可为 HF tokenizer 或 模型 ID 字符串
        # 缓存容量上限（极端长生成时可用以限制内存）
        cache_hard_limit_tokens: Optional[int] = None,
    ):
        # ---- 1) 确定 N，与官方对齐 ----
        self._N = _resolve_vocab_size(tokenizer=tokenizer, vocab_ids=vocab_ids)

        # ---- 2) 构造官方 logits processor 并注入 φ ----
        self._proc = PerturbationProcessor(N=self._N, id=id_mu)

        Fn = WatermarkingFnFourier if wm_fn.lower() == "fourier" else WatermarkingFnSquare
        phi = Fn(id=id_mu, k_p=int(k_p), N=self._N, kappa=float(kappa)).phi
        self._proc.set_phi(phi)

        # ---- 3) n-gram & auto-reset 状态 ----
        self._n_gram = int(n_gram)
        self._auto_reset = bool(auto_reset)
        if detect_mode not in ("batch", "row_any"):
            raise ValueError("detect_mode 只能是 'batch' 或 'row_any'")
        self._detect_mode = detect_mode  # "batch"：整批长度单调；"row_any"：任一样本重启即整批 reset

        # 记录“上一次长度”，用于检测新一轮生成
        self._prev_len_batch: Optional[int] = None
        self._prev_len_rows: Optional[List[int]] = None

        # 初始 reset（等价于官方“生成前 reset”）
        self._proc.reset(self._n_gram)

        # ---- 4) 检出相关的持久配置/状态（不影响嵌入路径） ----
        self._id_mu = int(id_mu)
        self._kappa = float(kappa)
        self._wm_fn = str(wm_fn)
        self._det_tokenizer = det_tokenizer if det_tokenizer is not None else tokenizer
        self._wm: Optional[Watermarker] = None  # 懒初始化，首次 detect 时创建

        # ---- 5) 侧信道缓存（仅在本轮生成期间累计 continuation token） ----
        self._cache_rows_ids: Optional[List[List[int]]] = None  # 每行样本的“新增 token”累积
        self._cache_limit = None if cache_hard_limit_tokens is None else int(cache_hard_limit_tokens)
        # 逐行记录“上一调用看到的长度”，用于精确提取新增 span（避免把提示词尾 token 计入）
        self._prev_seen_len_rows: Optional[List[int]] = None

        # ---- Performance counters (pure logits-processor overhead, accumulated per __call__) ----
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

    # 可选：显式手动 reset（与你的外部生命周期配合时可调用）
    def reset(self, n_gram: Optional[int] = None):
        if n_gram is not None:
            self._n_gram = int(n_gram)
        self._proc.reset(self._n_gram)
        self._prev_len_batch = None
        self._prev_len_rows = None
        self._cache_rows_ids = None  # 清空侧信道
        self._prev_seen_len_rows = None
        # timing counters are not reset here intentionally

    # —— 私有：在“发现新一轮生成开始”时，重置本地缓存 —— #
    def _reset_local_caches(self, bsz: int):
        self._cache_rows_ids = [[] for _ in range(bsz)]

    # HF LogitsProcessor 接口
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
        bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])

        need_reset = False
        if self._auto_reset:
            if self._detect_mode == "batch":
                # 批级检测：长度应严格递增；否则视为新一轮生成
                if self._prev_len_batch is None or cur_len <= self._prev_len_batch:
                    need_reset = True
                self._prev_len_batch = cur_len
            else:  # "row_any"
                if self._prev_len_rows is None or len(self._prev_len_rows) != bsz:
                    need_reset = True
                    self._prev_len_rows = [cur_len] * bsz
                else:
                    if any(cur_len <= pl for pl in self._prev_len_rows):
                        need_reset = True
                        self._prev_len_rows = [cur_len] * bsz
                    else:
                        self._prev_len_rows = [cur_len] * bsz

        if need_reset:
            # 重置官方扰动状态
            self._proc.reset(self._n_gram)
            # 重置侧信道缓存
            self._reset_local_caches(bsz)
            self._prev_seen_len_rows = [int(input_ids.shape[1])] * bsz  # 新一轮：基线为当前长度（不把提示词尾计入）

        # 若缓存还未初始化（例如 auto_reset=False 或首次调用）
        if self._cache_rows_ids is None or len(self._cache_rows_ids) != bsz:
            self._reset_local_caches(bsz)
        if self._prev_seen_len_rows is None or len(self._prev_seen_len_rows) != bsz:
            self._prev_seen_len_rows = [cur_len] * bsz  # 首次调用仅建立基线，不追加

        # —— 精确累计“本步新增的 continuation span”到缓存 —— #
        for i in range(bsz):
            prev = self._prev_seen_len_rows[i]
            if cur_len > prev:
                # 只把 [prev:cur_len) 这段真正新出现的 token 并入缓存
                new_span = input_ids[i, prev:cur_len].tolist()
                if new_span:
                    self._cache_rows_ids[i].extend(int(t) for t in new_span)
                    # 硬上限裁剪（可选）
                    if self._cache_limit is not None and len(self._cache_rows_ids[i]) > self._cache_limit:
                        overflow = len(self._cache_rows_ids[i]) - self._cache_limit
                        if overflow > 0:
                            self._cache_rows_ids[i] = self._cache_rows_ids[i][overflow:]
        # 更新基线长度
        self._prev_seen_len_rows = [cur_len] * bsz

        # 真实扰动：委托给官方实现（并计时，仅覆盖“扰动逻辑”本身）
        t0 = _time.perf_counter()
        try:
            out = self._proc(input_ids, scores)
            return out
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(_time.perf_counter() - t0)
                self._lp_calls += 1
            except Exception:
                pass

    def timing(self) -> Dict[str, Any]:
        """
        Return accumulated logits-processor runtime (waterfall perturbation part).
        Intended for server-side logging/benchmarking.
        """
        calls = int(self._lp_calls)
        total_s = float(self._lp_time_s)
        avg_us = (total_s / calls * 1e6) if calls > 0 else 0.0
        return {
            "lp_total_time_s": total_s,
            "lp_calls": calls,
            "lp_avg_per_call_us": float(avg_us),
        }

    def reset_timing(self) -> None:
        """Optional: reset timing counters for a clean measurement window."""
        self._lp_time_s = 0.0
        self._lp_calls = 0

    # ------------------- 离线检出（零参） ------------------- #
    def _ensure_watermarker(self) -> None:
        """
        懒初始化 Watermarker（仅在调用 detect_last 时触发）。
        注意：若你用 vocab_ids 推断 N 而未提供 tokenizer，则必须在构造时
        通过 det_tokenizer 显式提供检测所需的 tokenizer（HF 实例或模型 ID）。
        """
        if self._wm is not None:
            return
        if self._det_tokenizer is None:
            raise ValueError(
                "WaterfallLogitsProcessor.detect_last(): 需要 det_tokenizer/tokenizer 以构造 Watermarker。"
            )
        Fn = WatermarkingFnFourier if self._wm_fn.lower() == "fourier" else WatermarkingFnSquare
        # verify 时可传 k_p=None 自动抽取；这里占位 k_p=1 与官方 Detector 保持一致
        self._wm = Watermarker(
            tokenizer=self._det_tokenizer,
            id=int(self._id_mu),
            kappa=float(self._kappa),
            k_p=1,
            n_gram=int(self._n_gram),
            watermarkingFnClass=cast(Any, Fn),
        )

    def _decode_ids_to_text(self, ids: List[int]) -> str:
        if not ids:
            return ""
        tk = self._det_tokenizer
        # 优先使用标准 HF decode
        if hasattr(tk, "decode") and callable(getattr(tk, "decode")):
            return tk.decode(ids, skip_special_tokens=True)  # type: ignore[attr-defined]
        # 退化：尝试 ids->tokens->string
        if (
            hasattr(tk, "convert_ids_to_tokens")
            and hasattr(tk, "convert_tokens_to_string")
        ):
            toks = tk.convert_ids_to_tokens(ids)  # type: ignore[attr-defined]
            return tk.convert_tokens_to_string(toks)  # type: ignore[attr-defined]
        raise ValueError("det_tokenizer 无法解码 token ids，请在 builder 里传入 HF tokenizer 实例。")

    def _cached_texts(self) -> List[str]:
        """
        将“缓存的 continuation token”按行解码为文本。
        若没有缓存或缓存为空，返回空列表。
        """
        if self._cache_rows_ids is None:
            return []
        return [self._decode_ids_to_text(row) for row in self._cache_rows_ids]

    def detect_last(self) -> Dict[str, Any]:
        """
        零参检出：对“当前处理器缓存的 continuation 文本”逐行计算 q_score。
        返回字典：
          - "q_score": float 或 List[float]（单/多样本）
          - 可能包含 "k_p_extracted"（由底层 Watermarker 决定）
        在一次生成（一次“新轮”）结束后调用即可；无需向服务器透传任何参数。
        """
        self._ensure_watermarker()
        texts = self._cached_texts()
        if not texts:
            return {"error": "no_cached_tokens", "q_score": 0.0}

        res = self._wm.verify(  # type: ignore[union-attr]
            texts,
            id=[int(self._id_mu)],
            k_p=None,  # 允许自动抽取 k_p
            return_extracted_k_p=True,
            return_ranking=False,
            return_counts=False,
        )

        out: Dict[str, Any] = {}
        if isinstance(res, dict):
            q = np.asarray(res.get("q_score"))
            if q.ndim >= 1:
                try:
                    q_vec = np.squeeze(q)
                    if q_vec.ndim != 1 or q_vec.shape[0] != len(texts):
                        if q.ndim == 3 and q.shape[1] >= 1 and q.shape[2] >= 1:
                            q_vec = q[:, 0, 0]
                        elif q.ndim == 2 and q.shape[1] >= 1:
                            q_vec = q[:, 0]
                        else:
                            q_vec = q.reshape(len(texts), -1)[:, 0]
                except Exception:
                    q_vec = q
            else:
                q_vec = q

            if len(texts) == 1:
                out["q_score"] = float(np.asarray(q_vec).reshape(-1)[0])
            else:
                out["q_score"] = [float(x) for x in np.asarray(q_vec).reshape(-1)]

            if "k_p_extracted" in res:
                kpe = np.asarray(res["k_p_extracted"])
                if kpe.ndim == 2 and kpe.shape[1] >= 1:
                    kpe = kpe[:, 0]
                out["k_p_extracted"] = (
                    int(kpe.reshape(-1)[0]) if len(texts) == 1 else [int(x) for x in kpe.reshape(-1)]
                )
        else:
            q = np.asarray(res)
            if q.ndim == 3 and q.shape[1] >= 1 and q.shape[2] >= 1:
                q_vec = q[:, 0, 0]
            elif q.ndim == 2 and q.shape[1] >= 1:
                q_vec = q[:, 0]
            else:
                q_vec = np.squeeze(q)
                if q_vec.ndim != 1:
                    q_vec = q.reshape(len(texts), -1)[:, 0]
            out["q_score"] = (
                float(np.asarray(q_vec).reshape(-1)[0]) if len(texts) == 1 else [float(x) for x in np.asarray(q_vec).reshape(-1)]
            )
        # 检测完成后清理缓存，避免影响下一轮
        self.clear_cached()
        self._prev_seen_len_rows = None
        return out

    def clear_cached(self) -> None:
        """清空当前轮的 continuation 缓存（不影响扰动状态）。"""
        if self._cache_rows_ids is not None:
            for i in range(len(self._cache_rows_ids)):
                self._cache_rows_ids[i].clear()
