# RQ3 — performance overhead

The supplied RQ1/RQ2 workspaces retain online timing hooks but do not contain
the raw repetition-level records, shared-tokenizer counts, or normalization
table required to independently recompute main-paper Table X. This artifact
therefore marks RQ3 as incomplete instead of reconstructing point estimates
from the PDF.

Required completion files are listed by the numbered subdirectories. Add them
before changing `paper_reproduction/reproduce_rq3.sh` from a guard script to an
actual reproduction entry point.
