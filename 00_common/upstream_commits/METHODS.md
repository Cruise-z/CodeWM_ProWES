# Implementation provenance

| Component | Upstream / source | Revision available in workspace | Local implementation |
|---|---|---|---|
| ProWES logits implementation | `git@github.com:Cruise-z/CodeWM_ProWES_Logits.git` | `1d4f0cbad7fb76a31684b615dfe4f880ca7ee176` | `RQ1/source/` |
| MetaGPT reference checkout | `https://github.com/FoundationAgents/MetaGPT.git` | `02da62cabb9b04e205b901b12e190fc2f931394b` in the adjacent workspace; the experiment uses the frozen snapshot under `RQ1/source/reproduct/framework/` | RQ1 framework snapshot and patches |
| SWEET | `https://github.com/hongcheki/sweet-watermark` | Upstream commit was not recorded in the supplied RQ1 workspace | `RQ1/source/DT/codeGen/modelDeploy/` |
| WLLM | Paper implementation cited in source as `https://arxiv.org/abs/2301.10226` | Upstream repository/commit not recorded | `RQ1/source/DT/codeGen/modelDeploy/modelDeployer/libWM/wllm/` |
| EWD | Migrated/local adapter | Upstream repository/commit not recorded | `RQ1/source/DT/codeGen/modelDeploy/modelDeployer/libWM/ewd/` |
| STONE | Migrated/local adapter | Upstream repository/commit not recorded | `RQ1/source/DT/codeGen/modelDeploy/modelDeployer/libWM/stone/` |
| CodeIP | Migrated on 2026-08-17; per-file source hashes retained in `SOURCE_PROVENANCE.md` | Original checkout was not a Git repository | `RQ1/source/DT/codeGen/modelDeploy/modelDeployer/libWM/codeip/` |
| Waterfall | Migrated/local adapter | Upstream repository/commit not recorded | `RQ1/source/DT/codeGen/modelDeploy/modelDeployer/libWM/waterfall/` |
| SrcMarker | `https://github.com/YBRua/SrcMarker.git` | `2fb71cf816c12b0b07bb4d84dbe44ca0816662eb` before recorded local modifications | `RQ2/source/training/SrcMarker_fresh/` |
| CodeMark | `https://github.com/v587su/CodeMark.git` | Reference checkout `7958e66d083c9ab4bb3d5c1434f6a1df4bb670ff`; the paper's fresh run uses the unified local training pipeline | `RQ2/source/training/SrcMarker_fresh/` |

Unknown upstream revisions are stated explicitly because assigning a guessed
commit would weaken, rather than improve, artifact traceability. Before public
release, the authors should fill those rows from their original clone metadata
or retain patches against a confirmed upstream tag.
