# sweetLP.py
from __future__ import annotations
from typing import List, Dict, Optional
from math import sqrt

import torch
import time as _time
from torch import Tensor

# 复用你项目中 wllm.watermark 的基础类（保持嵌入逻辑不变）
from ..wllm.watermark import WatermarkLogitsProcessor
import scipy.stats


class SWEETLogitsProcessor(WatermarkLogitsProcessor):
    """
    SWEET 水印处理器（嵌入 + 离线零参检出一体化）
    - 严格保留 logits 偏置逻辑（仅在熵 > 阈值 且 greenlist 命中时 +delta）
    - 运行时自动缓存侧信道：prefix_len / full_ids（至当前步）/ 每步 entropy
    - 提供 detect_last() 零参接口；server 端无需透传任何参数
      （阈值等可在 regWM.py 构造时注入）
    """

    def __init__(
        self,
        *args,
        entropy_threshold: float = 0.9,
        tokenizer=None,                 # 可选，仅占位，零参检出不依赖
        z_threshold: float = 4.0,
        ignore_repeated_bigrams: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # ---- SWEET 配置（不改变嵌入逻辑）----
        self.entropy_threshold = float(entropy_threshold)
        self._tokenizer = tokenizer
        self._z_threshold = float(z_threshold)
        self._ignore_repeated_bigrams = bool(ignore_repeated_bigrams)
        if getattr(self, "rng", None) is None:
            self.rng = torch.Generator()

        # ---- 运行期缓存：用于零参离线检出 ----
        self._cache_prev_len: Optional[int] = None
        self._cache_prefix_len: Optional[int] = None
        self._cache_full_ids: Optional[torch.LongTensor] = None
        self._cache_entropy: List[float] = []
        
        # ---- Performance counters (pure logits-processor overhead, accumulated per __call__) ----
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

        # simple_1 播种至少需要 1 token 作为前缀
        self._min_prefix_len: int = 1 if getattr(self, "seeding_scheme", "simple_1") == "simple_1" else 1

    # =========== 保留原嵌入逻辑，仅末尾追加缓存 ===========
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        # Time ONLY the logits-processor path (pure watermark LP overhead)
        t0 = _time.perf_counter()
        try:
            # 懒初始化 RNG
            if self.rng is None:
                self.rng = torch.Generator()

            # 1) 逐样本计算 greenlist
            batched_greenlist_ids = [None for _ in range(input_ids.shape[0])]
            for b_idx in range(input_ids.shape[0]):
                greenlist_ids = self._get_greenlist_ids(input_ids[b_idx])
                batched_greenlist_ids[b_idx] = greenlist_ids

            green_tokens_mask = self._calc_greenlist_mask(scores=scores, greenlist_token_ids=batched_greenlist_ids)

            # 2) 计算下一 token 的分布熵（与 SWEET 论文一致）
            raw_probs = torch.softmax(scores, dim=-1)
            ent = -torch.where(raw_probs > 0, raw_probs * raw_probs.log(), raw_probs.new([0.0])).sum(dim=-1)  # [B]
            entropy_mask = (ent > self.entropy_threshold).view(-1, 1)

            # 3) 仅在高熵时刻启用 greenlist 偏置
            green_tokens_mask = green_tokens_mask * entropy_mask
            scores = self._bias_greenlist_logits(scores=scores, greenlist_mask=green_tokens_mask, greenlist_bias=self.delta)
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(_time.perf_counter() - t0)
                self._lp_calls += 1
            except Exception:
                pass

        # 4) ---- 运行时缓存（batch=1 场景）----
        #    - prefix_len：首步或检测到“新一轮生成”时记录
        #    - full_ids  ：保存到“当前步”的完整前缀+已生成 tokens
        #    - entropy   ：本步用于采样下一 token 的熵，按顺序追加
        try:
            bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])
            if bsz == 1:
                if self._cache_prev_len is None or cur_len <= self._cache_prev_len:
                    # 新一轮生成：重置缓存
                    self._cache_prefix_len = cur_len
                    self._cache_entropy = []
                self._cache_prev_len = cur_len
                # 到“当前步”为止的完整 token 序列（注意：可能比最终结果少最后 1 个 token）
                self._cache_full_ids = input_ids[0].detach().to("cpu").clone()
                # 记录本步熵（与即将生成的 token 对齐）
                self._cache_entropy.append(float(ent[0].item()))
        except Exception:
            pass  # 缓存失败不影响主流程

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

    # =========== 离线零参检出（与 SweetDetector 逻辑对齐） ===========
    @staticmethod
    def _compute_z_score(observed_green: int, T: int, gamma: float) -> float:
        expected = gamma
        numer = observed_green - expected * T
        denom = sqrt(max(1e-12, T * expected * (1 - expected)))
        return float(numer / denom)

    @staticmethod
    def _compute_p_value(z: float) -> float:
        return float(scipy.stats.norm.sf(z))

    def _score_sequence(
        self,
        input_ids: Tensor,
        prefix_len: int,
        entropy: List[float],
        *,
        return_num_tokens_scored: bool = True,
        return_num_green_tokens: bool = True,
        return_watermarking_fraction: bool = True,
        return_green_fraction: bool = True,
        return_green_token_mask: bool = False,
        return_z_score: bool = True,
        return_p_value: bool = True,
    ) -> Dict:
        if self._ignore_repeated_bigrams:
            raise NotImplementedError("ignore_repeated_bigrams=True 尚未实现（与原实现一致）")

        out: Dict = {}
        prefix_len = max(self._min_prefix_len, int(prefix_len))
        num_tokens_generated = int(len(input_ids) - prefix_len)
        if num_tokens_generated < 1:
            out["invalid"] = True
            return out

        # 与 SweetDetector 对齐：仅对熵 > 阈值 的位置计入统计
        if len(entropy) != len(input_ids):
            # 对齐：前缀部分补 0.0（不会被计入），其余保持记录顺序
            if len(entropy) == num_tokens_generated:
                entropy = [0.0] * prefix_len + list(entropy)
            else:
                raise ValueError(f"entropy length mismatch: got {len(entropy)} vs ids {len(input_ids)}")

        scored_positions = [i for i in range(prefix_len, len(input_ids)) if entropy[i] > self.entropy_threshold]
        num_tokens_scored = len(scored_positions)
        if num_tokens_scored < 1:
            # 认为近似“人类生成”
            return {
                "num_tokens_generated": num_tokens_generated,
                "num_tokens_scored": 0,
                "num_green_tokens": 0,
                "watermarking_fraction": 0.0,
                "green_fraction": 0.0,
                "z_score": -100.0,
                "p_value": 1.0,
            }

        green_token_count, green_token_mask = 0, []
        for idx in range(prefix_len, len(input_ids)):
            curr_token = int(input_ids[idx])
            greenlist_ids = self._get_greenlist_ids(input_ids[:idx])
            if entropy[idx] > self.entropy_threshold:
                if curr_token in set(int(t) for t in greenlist_ids):
                    green_token_count += 1
                    green_token_mask.append(True)
                else:
                    green_token_mask.append(False)
            else:
                green_token_mask.append(False)

        out["num_tokens_generated"] = num_tokens_generated
        if return_num_tokens_scored:
            out["num_tokens_scored"] = num_tokens_scored
        if return_num_green_tokens:
            out["num_green_tokens"] = int(green_token_count)
        if return_watermarking_fraction:
            out["watermarking_fraction"] = float(num_tokens_scored / max(1, num_tokens_generated))
        if return_green_fraction:
            out["green_fraction"] = float(green_token_count / max(1, num_tokens_scored))
        if return_z_score:
            z = self._compute_z_score(green_token_count, num_tokens_scored, float(self.gamma))
            out["z_score"] = z
        if return_p_value:
            z = out.get("z_score")
            if z is None:
                z = self._compute_z_score(green_token_count, num_tokens_scored, float(self.gamma))
            out["p_value"] = self._compute_p_value(float(z))
        if return_green_token_mask:
            out["green_token_mask"] = green_token_mask
        return out

    def detect_last(self) -> Dict:
        """
        零参离线检出：利用生成阶段缓存的 full_ids / prefix_len / entropy
        用法：proc.detect_last()  // 全部为可选参数，服务器无需透传
        """
        if self._cache_full_ids is None or self._cache_prefix_len is None:
            raise RuntimeError("No cached sequence for detection. Generate with this processor first.")

        full_ids: Tensor = self._cache_full_ids
        prefix_len: int = int(self._cache_prefix_len)
        # 对齐：把记录的“生成期熵”（只覆盖生成区间）扩展成与 ids 等长的列表
        entropy_full = [0.0] * prefix_len + list(self._cache_entropy[: max(0, len(full_ids) - prefix_len)])

        out: Dict = {}
        score = self._score_sequence(
            input_ids=full_ids,
            prefix_len=prefix_len,
            entropy=entropy_full,
            return_num_tokens_scored=True,
            return_num_green_tokens=True,
            return_watermarking_fraction=True,
            return_green_fraction=True,
            return_green_token_mask=False,
            return_z_score=True,
            return_p_value=True,
        )
        out.update(score)

        thr = float(self._z_threshold)
        if score.pop("invalid", False):
            out["invalid"] = True
            return out
        pred = bool(float(score["z_score"]) > thr)
        out["prediction"] = pred
        if pred:
            out["confidence"] = float(1.0 - float(score.get("p_value", 1.0)))
        
        # 检测完成后清理一次缓存，避免“脏轨迹”影响下一轮
        self._cache_full_ids = None
        self._cache_prefix_len = None
        self._cache_prev_len = None
        self._cache_entropy = []
        return out
