import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "project" / "srcMarker" / "SrcMarker" / "3_analysis.py"
spec = importlib.util.spec_from_file_location("analysis3", P)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_delta_bar_and_mar_chance():
    rows = [
        {"watermark": [1,0,1,0], "extract": [1,0,1,0], "obfus_extract": [1,1,1,0]},
        {"watermark": [0,1,0,1], "extract": [0,1,0,1], "obfus_extract": [1,0,0,1]},
    ]
    metrics, paired = m.summarize(rows)
    assert metrics["clean_BAR"] == 1.0
    assert metrics["attack_BAR"] == 0.625
    assert metrics["DeltaBAR"] == 0.375
    assert metrics["chance_MAR"] == 0.0625


def test_status_breakdown_is_explicit(tmp_path):
    rows = [
        {"watermark": [1], "extract": [1], "obfus_extract": [0],
         "attack_meta": {"status": "valid_attack", "changed": True, "syntax_valid": True}},
        {"attack_meta": {"status": "no_op", "changed": False, "syntax_valid": True}},
    ]
    path = tmp_path / "rows.jsonl"
    path.write_text("".join(__import__("json").dumps(x) + "\n" for x in rows))
    loaded = m.read_jsonl(path)
    attempted = len(loaded)
    assert attempted == 2
