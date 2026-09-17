import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "project" / "srcMarker" / "SrcMarker" / "run_watermark_detector.py"


def test_detector_dry_run(tmp_path):
    p = tmp_path / "attack.jsonl"
    rows = [
        {"_attack_uid":"a", "after_obfus":"int f(){return 1;}", "attack_meta":{"syntax_valid":True, "changed":True}},
        {"_attack_uid":"b", "after_obfus":"", "attack_meta":{"syntax_valid":False, "changed":False}},
    ]
    p.write_text("".join(json.dumps(x)+"\n" for x in rows))
    cp = subprocess.run([sys.executable, str(SCRIPT), "--attack-jsonl", str(p),
                         "--merged-output", str(tmp_path/"out.jsonl"),
                         "--checkpoint-path", "dummy.pt", "--lang", "java",
                         "--dataset", "csn_java", "--dry-run"],
                        text=True, capture_output=True, check=True)
    assert "rows=2 detector_eligible=1" in cp.stdout


def test_detector_dry_run_excludes_no_op(tmp_path):
    p = tmp_path / "attack.jsonl"
    rows = [
        {"_attack_uid":"a", "after_obfus":"int f(){return 1;}",
         "attack_meta":{"syntax_valid":True, "changed":False, "status":"no_op"}},
    ]
    p.write_text("".join(json.dumps(x)+"\n" for x in rows))
    cp = subprocess.run([sys.executable, str(SCRIPT), "--attack-jsonl", str(p),
                         "--merged-output", str(tmp_path/"out.jsonl"),
                         "--checkpoint-path", "dummy.pt", "--lang", "java",
                         "--dataset", "csn_java", "--dry-run"],
                        text=True, capture_output=True, check=True)
    assert "rows=1 detector_eligible=0" in cp.stdout
