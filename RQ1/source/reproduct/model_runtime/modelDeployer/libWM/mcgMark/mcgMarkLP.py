"""CodeWM outer adapter for the released MCGMark logits processor."""

from . import watermark_global
from . import watermark_processor


MCGMarkLogitsProcessor = watermark_processor.WatermarkLogitsProcessor


def build_codewm(resources, params):
    """Construct MCGMark while preserving its released module-state hooks."""
    old_water_info = str(params.get("watermark_info", "000000000000"))
    if len(old_water_info) != 12 or set(old_water_info) - {"0", "1"}:
        raise ValueError("MCGMark watermark_info must be a 12-bit binary string")

    watermark_global.set_value("old_water_info", old_water_info)
    if not hasattr(watermark_processor, "get_old_water_info"):
        watermark_processor.get_old_water_info = (
            lambda: watermark_global.get_value("old_water_info")
        )
    if not hasattr(watermark_processor, "get_waterinfo_12_global"):
        watermark_processor.get_waterinfo_12_global = (
            lambda: watermark_global.get_value("waterinfo_12")
        )
    if not hasattr(watermark_processor, "set_waterinfo_12_global"):
        watermark_processor.set_waterinfo_12_global = (
            lambda value: watermark_global.set_value("waterinfo_12", value)
        )

    return MCGMarkLogitsProcessor(
        vocab=resources.vocab_ids(),
        gamma=float(params.get("gamma", 0.5)),
        delta=float(params.get("delta", 6.0)),
        tokenizer=resources.tokenizer,
        hash_key=int(params.get("hash_key", 666)),
    )
