# Copyright 2025 CodeWM_AutoTest.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ==============================================================================
# stoneLP.py
# Description: Minimal wrapper: reuse original STONEUtils / STONELogitsProcessor
# - No dependency on STONEConfig (we use a thin _ConfigShim)
# - Keep original logits biasing logic untouched (super().__call__())
# - Cache full input_ids during generation and provide zero-arg detect_last()
# ==============================================================================
from __future__ import annotations
from typing import Any, Dict, List, Optional

import torch
import time as _time
from torch import Tensor

# 请按你的项目结构调整导入路径：
# 假设 stone.py 与本文件同目录
from .stone import STONEUtils, STONELogitsProcessor


class _ConfigShim:
    """
    仅提供 STONEUtils / STONELogitsProcessor 运行所需的属性，
    以替代 STONEConfig；参数由 regWM.py 在构造时传入。
    """
    def __init__(
        self,
        *,
        tokenizer,              # generation_tokenizer
        vocab_size: int,
        device,                 # torch.device 或 str
        gamma: float,
        delta: float,
        hash_key: int,
        z_threshold: float,
        prefix_length: int,
        language: str,
        # 下方两个仅为保持接口相容性；本包装不使用 generation_model/gen_kwargs
        model: Optional[Any] = None,
        gen_kwargs: Optional[Dict[str, Any]] = None,
    ):
        # stone.py 里用到的字段名保持一致
        self.generation_tokenizer = tokenizer
        self.vocab_size = int(vocab_size)
        self.device = device
        self.gen_kwargs = {} if gen_kwargs is None else gen_kwargs

        self.gamma = float(gamma)
        self.delta = float(delta)
        self.hash_key = int(hash_key)
        self.z_threshold = float(z_threshold)
        self.prefix_length = int(prefix_length)
        self.language = str(language)

        # 仅占位，原始偏置逻辑不需要 model
        self.model = model


class STONEWMLogitsProcessor(STONELogitsProcessor):
    """
    复用原始 STONELogitsProcessor 的偏置逻辑；
    仅新增：
      - 在 __init__ 里用 _ConfigShim 注入参数（无 STONEConfig 依赖）
      - 在 __call__ 后缓存本轮最新的 full input_ids（逐行）
      - detect_last(): 基于缓存做零参离线检测（用原 STONEUtils.score_sequence）
    """

    def __init__(
        self,
        *,
        tokenizer,
        vocab_size: int,
        device,
        gamma: float,
        delta: float,
        hash_key: int,
        z_threshold: float,
        prefix_length: int,
        language: str,
        watermark_on_pl: str = "True",
        skipping_rule: Optional[str] = None,
    ):
        # 1) 构造轻量“配置”并复用原工具类/处理器
        cfg = _ConfigShim(
            tokenizer=tokenizer,
            vocab_size=vocab_size,
            device=device,
            gamma=gamma,
            delta=delta,
            hash_key=hash_key,
            z_threshold=z_threshold,
            prefix_length=prefix_length,
            language=language,
        )
        utils = STONEUtils(
            cfg,
            skipping_rule=skipping_rule,
            watermark_on_pl=watermark_on_pl,
            language=language,
        )
        # 2) 调父类构造器（保持原行为）
        super().__init__(
            config=cfg,
            utils=utils,
            skipping_rule=skipping_rule,
            watermark_on_pl=watermark_on_pl,
            language=language,
        )

        # 3) 仅新增：检出用缓存（不影响偏置逻辑）
        self._cache_full_ids_rows: Optional[List[Tensor]] = None
        self._prev_len_rows: Optional[List[int]] = None
        self._cache_bsz: Optional[int] = None

        # 4) Performance counters (pure logits-processor overhead, accumulated per __call__)
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

    # —— 不改原偏置逻辑：调用父类 __call__，随后追加缓存 —— #
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:

        # Time ONLY the logits-processor path (pure watermark LP overhead)
        t0 = _time.perf_counter()
        try:
            scores_out = super().__call__(input_ids, scores)  # 原逻辑不变
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(_time.perf_counter() - t0)
                self._lp_calls += 1
            except Exception:
                pass

        # 追加：缓存本轮“完整 input_ids”（逐行），用于零参检测
        try:
            bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])
            need_reset = (
                self._cache_full_ids_rows is None
                or self._prev_len_rows is None
                or self._cache_bsz is None
                or self._cache_bsz != bsz
                or any(cur_len <= pl for pl in (self._prev_len_rows or []))
            )
            if need_reset:
                self._cache_full_ids_rows = [torch.empty(0, dtype=input_ids.dtype) for _ in range(bsz)]
                self._prev_len_rows = [0] * bsz
                self._cache_bsz = bsz

            for i in range(bsz):
                self._cache_full_ids_rows[i] = input_ids[i].detach().to("cpu").clone()
                self._prev_len_rows[i] = cur_len
        except Exception:
            pass  # 缓存失败不影响生成

        return scores_out

    # —— 零参离线检测：与原逻辑对齐（decode → re-tokenize(no special tokens) → score） —— #
    def detect_last(self) -> Dict[str, Any]:
        """
        使用生成阶段缓存的 full input_ids 零参检测。
        与源实现保持一致：先将缓存的 ids 解码为文本，再以
        add_special_tokens=False 重新分词得到 ids 后再评分。
        返回：
          单行：{"is_watermarked": bool, "score": float}
          多行：{"is_watermarked": List[bool], "score": List[float]}
        """
        if not self._cache_full_ids_rows:
            return {"error": "no_cached_tokens"}

        results_bool: List[bool] = []
        results_score: List[float] = []

        for ids_cpu in self._cache_full_ids_rows:
            if ids_cpu.numel() == 0:
                results_bool.append(False)
                results_score.append(float("-inf"))
                continue

            try:
                # 1) 解码为纯文本（跳过特殊符号）
                tok = getattr(self.config, "generation_tokenizer", None)  # type: ignore[attr-defined]
                if tok is None:
                    raise RuntimeError("no_tokenizer")
                text = tok.decode(ids_cpu.tolist(), skip_special_tokens=True)
                if not text:
                    # 空文本无法检测：给出 -inf
                    results_bool.append(False)
                    results_score.append(float("-inf"))
                    continue

                # 2) 以 add_special_tokens=False 重新分词得到 ids
                enc = tok(text, return_tensors="pt", add_special_tokens=False)
                new_ids_cpu = enc["input_ids"][0]
                if new_ids_cpu.numel() == 0:
                    results_bool.append(False)
                    results_score.append(float("-inf"))
                    continue

                ids = new_ids_cpu.to(self.config.device, non_blocking=True)  # type: ignore[attr-defined]

                # 3) 打分（STONEUtils.score_sequence 返回 (z, flags, weights)）
                z_score, _, _ = self.utils.score_sequence(ids)
            except Exception:
                # 与源实现对齐：发生异常（如长度不足）时返回 -inf
                z_score = float("-inf")

            thr = float(self.config.z_threshold)  # type: ignore[attr-defined]
            results_bool.append(bool(z_score > thr))
            results_score.append(float(z_score))

        if len(results_bool) == 1:
            return {"is_watermarked": results_bool[0], "score": results_score[0]}
        return {"is_watermarked": results_bool, "score": results_score}

    def timing(self) -> Dict[str, Any]:
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

    def clear_cached(self) -> None:
        """可选：手动清空缓存（不影响偏置状态）。"""
        self._cache_full_ids_rows = None
        self._prev_len_rows = None
        self._cache_bsz = None
