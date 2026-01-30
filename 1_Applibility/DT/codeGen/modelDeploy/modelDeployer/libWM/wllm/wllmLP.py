# wllmLP.py
# 将检出逻辑“收编”为 WatermarkLogitsProcessor 的方法版本
# 说明：
# - 不修改原文件；通过继承保持完全兼容的嵌入逻辑
# - 将 WLLM 的 Detector 以离线零参检出方式收编进 logits processor
# - 在运行时自动缓存所需侧信道数据 (prefix_len、full_ids) 用于Detector检测

from __future__ import annotations
from math import sqrt
from typing import Dict, Optional, List

import torch
import time as _time
from torch import Tensor
import scipy.stats

# 复用你项目里的基础实现
from .watermark import WatermarkBase, WatermarkLogitsProcessor


class WLLMLogitsProcessor(WatermarkLogitsProcessor):
    """
    在严格保留“水印嵌入/偏置”调用逻辑的前提下，
    将 Detector 的检出逻辑以**离线零参**形式收编进处理器：
      - 运行时自动缓存：prefix_len / full_ids（batch=1 场景）
      - 提供 detect_last()：无需 server 透传任何 ids/entropy 等
      - 与 WatermarkDetector 的 z/p 计算、假设检验完全对齐
    """

    def __init__(
        self,
        *args,
        tokenizer=None,                 # 可选，仅作扩展使用；当前零参检测不依赖
        z_threshold: float = 4.0,
        ignore_repeated_bigrams: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # ---- 检测期配置（不影响嵌入逻辑）----
        self._tokenizer = tokenizer
        self._z_threshold = float(z_threshold)
        self._ignore_repeated_bigrams = bool(ignore_repeated_bigrams)
        if getattr(self, "rng", None) is None:
            self.rng = torch.Generator()

        # ---- 运行时缓存（用于零参检出）----
        self._cache_prev_len: Optional[int] = None
        self._cache_prefix_len: Optional[int] = None
        self._cache_full_ids: Optional[torch.LongTensor] = None

        # ---- Performance counters (pure logits-processor overhead, accumulated per __call__) ----
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

        # simple_1 播种至少需要一个 token 作为前缀
        self._min_prefix_len: int = 1 if getattr(self, "seeding_scheme", "simple_1") == "simple_1" else 1

    # -------------- 保留原嵌入逻辑（仅在末尾追加缓存） --------------
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        # Time ONLY the logits-processor path (pure watermark LP overhead)
        t0 = _time.perf_counter()
        try:
            # 直接复用上游 WatermarkLogitsProcessor.__call__()
            # 保证嵌入逻辑与原实现完全一致、无“手写复刻偏离”风险
            scores_out = super().__call__(input_ids, scores)
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(_time.perf_counter() - t0)
                self._lp_calls += 1
            except Exception:
                pass

        # ---- 运行时缓存：用于零参检出（仅 batch=1；多 batch 可按需扩展为列表态）----
        try:
            bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])
            if bsz == 1:
                if self._cache_prev_len is None or cur_len <= self._cache_prev_len:
                    # 视为“新一轮生成”开始：当前长度即为 prefix_len
                    self._cache_prefix_len = cur_len
                self._cache_prev_len = cur_len
                # 保存完整序列（拷贝到 CPU，避免显存占用 & 生命周期问题）
                self._cache_full_ids = input_ids[0].detach().to("cpu").clone()
        except Exception:
            # 缓存失败不影响主流程
            pass

        return scores

    def timing(self) -> Dict[str, float]:
        """
        Return accumulated logits-processor runtime.
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

    # ---------------------- 以下为离线检出实现 ----------------------
    @staticmethod
    def _compute_z_score(green_count: int, T: int, gamma: float) -> float:
        expected = gamma
        numer = green_count - expected * T
        denom = sqrt(max(1e-12, T * expected * (1 - expected)))
        return float(numer / denom)

    @staticmethod
    def _compute_p_value(z: float) -> float:
        return float(scipy.stats.norm.sf(z))

    def _score_sequence(
        self,
        input_ids: Tensor,
        prefix_len: int,
        return_num_tokens_scored: bool = True,
        return_num_green_tokens: bool = True,
        return_green_fraction: bool = True,
        return_green_token_mask: bool = False,
        return_z_score: bool = True,
        return_p_value: bool = True,
    ) -> Dict:
        """
        与 WatermarkDetector._score_sequence 对齐：
          - 遍历 prefix_len..len(ids)-1，每步用 _get_greenlist_ids(seed_ids) 判定命中
          - 统计 G、T，并计算 z/p
        """
        score_dict: Dict = {}
        if self._ignore_repeated_bigrams:
            raise NotImplementedError("ignore_repeated_bigrams=True 尚未实现（与官方实现一致）")

        prefix_len = max(self._min_prefix_len, int(prefix_len))
        num_tokens_scored = int(len(input_ids) - prefix_len)
        if num_tokens_scored < 1:
            score_dict["invalid"] = True
            return score_dict

        green_token_count, green_token_mask = 0, []
        for idx in range(prefix_len, len(input_ids)):
            curr_token = int(input_ids[idx])
            greenlist_ids = self._get_greenlist_ids(input_ids[:idx])
            if curr_token in set(int(t) for t in greenlist_ids):
                green_token_count += 1
                green_token_mask.append(True)
            else:
                green_token_mask.append(False)

        if return_num_tokens_scored:
            score_dict["num_tokens_scored"] = int(num_tokens_scored)
        if return_num_green_tokens:
            score_dict["num_green_tokens"] = int(green_token_count)
        if return_green_fraction:
            score_dict["green_fraction"] = float(green_token_count / num_tokens_scored)
        if return_z_score:
            score_dict["z_score"] = self._compute_z_score(
                green_token_count, num_tokens_scored, float(self.gamma)
            )
        if return_p_value:
            z = score_dict.get("z_score")
            if z is None:
                z = self._compute_z_score(green_token_count, num_tokens_scored, float(self.gamma))
            score_dict["p_value"] = self._compute_p_value(float(z))
        if return_green_token_mask:
            score_dict["green_token_mask"] = green_token_mask

        return score_dict

    def detect_last(self) -> Dict:
        """
        零参离线检出：基于生成期间自动缓存的 full_ids/prefix_len 完成检出。
        默认：返回分数与判决，阈值取初始化的 self._z_threshold。
        """
        if self._cache_full_ids is None or self._cache_prefix_len is None:
            raise RuntimeError("No cached sequence for detection. Run generate() with this processor first.")

        full_ids = self._cache_full_ids
        pre_len = int(self._cache_prefix_len)

        out: Dict = {}
        # 1) 打分（与 WatermarkDetector._score_sequence 对齐）
        score_dict = self._score_sequence(input_ids=full_ids, prefix_len=pre_len)
        out.update(score_dict)
        # 若文本过短，直接返回 invalid
        if out.pop("invalid", False):
            self._last_detection = {"invalid": True}
            # 清理一次轨迹缓存，避免下一轮误用
            self._cache_full_ids = None
            self._cache_prefix_len = None
            self._cache_prev_len = None
            return {"invalid": True}
        # 2) 进行假设检验并补齐 z/p
        if "z_score" not in out:
            T = int(out.get("num_tokens_scored", 0))
            G = int(out.get("num_green_tokens", 0))
            z = self._compute_z_score(G, T, float(self.gamma))
            out["z_score"] = float(z)
            out["p_value"] = self._compute_p_value(float(z))
        thr = float(self._z_threshold)
        out["prediction"] = bool(float(out["z_score"]) > thr)
        if out["prediction"]:
            out["confidence"] = float(1.0 - float(out.get("p_value", 1.0)))
        # 3) 记录最近一次结果并清除轨迹缓存
        self._last_detection = dict(out)
        self._cache_full_ids = None
        self._cache_prefix_len = None
        self._cache_prev_len = None
        return out