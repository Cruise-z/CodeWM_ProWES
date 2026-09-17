# CodeIP Source Provenance

The runtime and training logic in this package was migrated from
`/home/zhaorz/project/CodeWM/temp/codeip` on 2026-08-17.

The deployment package keeps the existing flattened import layout used by
CodeWM and the `codeipLP.py` adapter. The following released assets are retained:

- random multi-bit message model and logits processor;
- PDA/type message model and logits processor;
- standalone generation entry and complete argument dataclass;
- Java PDA type-predictor checkpoint;
- type-predictor training script, dataset downloader, and training guide.

The copied Java checkpoint SHA-256 is
`6f83b7495154500c9bf531a8045d680621adaf93f3f3f1897676b38fbdde0708`.

The source-file SHA-256 values recorded before import adaptation are:

- `wm.py`: `a899b90226f5d653dee38d1b7bdd22f793f9f58ef5cd67abcdad7c5d3b096276`
- `message_model_processor.py`: `18257ee18dd4d19b6e9c21b92090b7b502763a9a55e336405e3cae5a210aad66`
- `wm_arg_class.py`: `1da75858c7908f5e05f9d526ca0ef720e79e2d5d6979a86b4b6a5f92b37624b0`
- `run_wm.py`: `50e98ffe5477b62289fbe589a23dd96c8e86723cc6fa1e38b0a0c469858e89a0`
- `train_tp_model.py`: `b1bee32d44ba57146ae61d4c6daf567697529d97451dadf0d760e73024f8dff7`
- `dataset.py`: `0e51062f2654210f4b7d379a9df4dba318d6367384eac7956748f4c8c336aea6`

The deployed Java checkpoint uses embedding size 128 and hidden size 256.
Those two flags must be passed when reproducing it because the released trainer
defaults are smaller. Run the standalone generator as a package module from the
deployer directory: `python -m libWM.codeip.run_wm`.

Bulk experimental outputs and the downloaded Java training corpus are not part
of deployment and were intentionally not copied. They remain under the source
tree. This package does not claim checkpoints for Python, Go, JavaScript, or PHP;
those languages require an explicit `pda_model_path` or a newly trained package
checkpoint.
