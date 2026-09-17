# Available timing hooks and missing harness metadata

Available source hooks:

- logits-bias generation boundary: `../../RQ1/source/DT/codeGen/modelDeploy/modelDeployer/generation.py`;
- per-method logits processor timing: `../../RQ1/source/DT/codeGen/modelDeploy/modelDeployer/libWM/`;
- SrcMarker embedding/extraction timing: `../../RQ2/source/training/SrcMarker_fresh/eval_main.py`.

Still required: the exact warm-up protocol, repetitions, synchronization
boundary, watermark-free baseline harness, shared tokenizer revision, and the
script that normalizes raw milliseconds to ms/1K reference tokens.
