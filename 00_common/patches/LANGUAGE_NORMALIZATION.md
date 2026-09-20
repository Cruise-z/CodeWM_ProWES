# English-language normalization

Language-only integration edits were applied after importing the frozen RQ1
and RQ2 source snapshots. They change reviewer-facing comments, documentation,
configuration descriptions, and report labels; they do not alter algorithms
or released observations.

## RQ1 traceability

The pristine source is identified by commit
`9c647f9a8d4e9bd519aefac7c0a8b6dc501cafaa`. The artifact-level
`ARTIFACT_MANIFEST.json` records every post-normalization hash. Representative
pre/post hashes are:

The two historical direct-generation examples listed below were later removed
together with their incomplete prompt package. They remain available in the
pre-removal backup tag
`artifact-backup-before-legacy-dt-removal-20260917`; their hashes are retained
here as integration provenance.

| File | Original SHA-256 | Released SHA-256 |
|---|---|---|
| `DT/codeGen/agent.py` | `ddf28ef10455cc5da090fca8d37fdb06a9d80bc6fcac8099672721bd96fdfc35` | `bbd9674257a34d20ce99b434f365f65271c67fc63f35b99375672e411146b1b8` |
| `DT/codeGen/agentArchGen.py` | `a79d2a2f4c3c6d68cfaa092608a10242c6a2ed703cb8997c012a0ff8bf635a51` | `ed39fc1f435b5c5fb87d1355df4c6b6596d2508ca1ef342a6598cd1e68cbf558` |
| `DT/codeGen/README.md` | `9f88c89c87aabbe4833085716e0ae76d4f9e7d364e8c7afd34791bd729f01772` | `4f2a4ea1cd166bc0b1323c56172e46e0abd6f487c656948530702876ceb4a42b` |
| `reproduct/REPRODUCIBILITY.md` | `c7226537eb37905f47230e5909048915882183366cb73aab6a5f7ca2e902cf1e` | `a0a26904ed8ae1b753646fe3886379651b59bc57fb92fff2a04e3243675c9e0c` |
| `reproduct/campaign.py` | `6927c0dd5951d13ef20b327061c16e63e93da4c09e97de35edfa58ccd53c8c38` | `33c4aac60594366475d157a3f380a8db8d19916111bcf47e883e16d18c04d255` |

The historical Java prompt-template copies received the same comment-only
English translation before that incomplete prompt package was removed. The
two released example batch configurations are operationally equivalent
English rewrites with SHA-256
`491ba7bbab8d9eb2c8d1ab202984ad0aface71fcf959289017d822e6a61d2b8f`.
Evaluator comments and documentation were translated in both synchronized
copies (`RQ1/04_docker/` and `RQ1/source/reproduct/evaluator/`).

## RQ2 traceability

The original curated hashes remain in `RQ2/source/SOURCE_MANIFEST.json`; the
root artifact manifest records the released hashes.

| File | Curated SHA-256 | Released SHA-256 |
|---|---|---|
| `build_final_report.py` | `eb40d080656c68225b171f62b103782b0710bbfe2929c6d1b8be7f784bff8bdf` | `e7ffc130b3f314783cf9308f64c59586a186b9cf837e2f734bc887e6ac010a97` |
| `build_fresh_report.py` | `a66b61100ab8611c06184472ae6c75c146f781f28ab5445a18b94561bc9f138d` | `bf342c056120edffe6d1ad39774212e8ced7c5a421f53d95c82a3fac40af3d0b` |
| `build_full_epr_report.py` | `2108f859818c760d8ca7e688195d913ebc934ef4df58eb482733251f09454dbe` | `a424b99b0143e523ff1a71ec47415a31fcca9d9cb9d328be3bbaa6afce5019af` |
| `build_llm_pilot_report.py` | `33ff9ddb1672351c2f9d5bd61caef6a27f6ba0ae449805c2088a551b6bc77fd5` | `80008ea5031fb29b07f3fa99d94af6b7af5559efc69aaeb22b45fa0e053616fe` |
| `build_rq2_deliverables.py` | `73143938bd45a80f75204299daffaad847484d0131047e23ba178de13635389a` | `99952ed0b8ed043d3bca23421572bd95b4a194081cbd7dae59ce77564041f47a` |

The four formerly CJK-bearing SrcMarker source files now use equivalent English
comments and an English legacy `NotImplementedError` message. These edits do
not affect successful transformation paths or released observations.
