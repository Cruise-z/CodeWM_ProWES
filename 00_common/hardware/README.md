# Hardware records

The RQ1 preflight capture in `../environment/preflight.json` records the full
host, CUDA, GPU, model-service, and container inspection output. The captured
host used NVIDIA A800 80GB PCIe GPUs. The RQ2 paper report records Python
3.13.5, PyTorch 2.6.0+cu124, NVIDIA A800 80GB, g++ 11.4, Java 21, and Node 22.

Hardware records are historical observations, not requirements for reading or
rebuilding the released tables. Byte-identical RQ1 model replay has the tighter
GPU/software boundary described in `RQ1/source/reproduct/REPRODUCIBILITY.md`.
