# CodeWM_ProWES: Project-Structured Evaluation for LLM-Generated Code Watermarking

This repository contains the reference implementation and artifact for the paper:

**“A Systematic Empirical Study on the Properties of Watermarking for LLM-Generated Code”** (ISSTA 2026)

It provides:
- **ProWES** (**Pro**ject-structured **W**atermarking **E**valuation **S**ystem) for end-to-end evaluation of **logits-bias** watermarking on *multi-file, buildable, executable* repositories.
- **metaProjectDEV**, a *project-level* benchmark dataset for measuring applicability + detectability of logits-bias watermarks.
- A **randomized, channel-stratified, strength-controlled transformation** framework for robustness evaluation of **semantic-preserving** watermarking methods.
- Scripts to reproduce paper results for **RQ1 / RQ2 / RQ3**.

> Note: Stage-0 architecture synthesis uses MetaGPT + a proprietary LLM API in the paper setup. The artifact is designed to be reproducible via provided checkpoints / prepared datasets; if you want to re-run Stage-0, you’ll need your own compatible API access.

---

## Applibility test:

**ProWES** is a 3-stage pipeline tailored for project-structured code watermark evaluation:

![image-20260130204056144](./README.assets/image-20260130204056144.png)

- **Stage 0 — Architecture Synthesis**
  - Generates an “ideal” repository blueprint (file list, data structures, interfaces, call flow) and a self-test suite.
- **Stage 1 — Checkpointed Code Generation**
  - Resumes from Stage-0 checkpoint; generates multi-file source code with **watermark embedded during decoding** (logits-bias watermarking).
- **Stage 2 — Automated Docker Test**
  - Builds and runs the repository in Docker; classifies runtime outcomes (Pass / Compilation Error / Runtime Error / Test Error).

This setup exposes failures that snippet/function-level benchmarks cannot capture (e.g., cross-file consistency, dependency resolution, build/test integration).

### Instructions for Use

1. `./1_Applibility/datasets` contains some of the prompts used in the evaluation, along with the generated code repositories.
2. The remaining content is located in the subfolders under `./1_Applibility/DT`. Each subfolder includes a `README.md` file with instructions for use, so please refer to those files when operating it.

We will further refine the overall layout in future updates to improve readability and make reproduction more convenient.

## Robustness test:

Inspired by Dual-Channel Constraints theory, we construct a hierarchical code transformation framework. This framework supports multiple programming languages and provides a diverse set of transformations. In the following, we evaluate the robustness of existing semantic-preserving watermarking methods under randomized, channel-stratified code transformation attacks:![image-20260130205112564](./README.assets/image-20260130205112564.png)

### Instructions for Use

1. `./2_Robustness` contains the obfuscators constructed in the paper.
2. `./2_Robustness/project` contains the adaptation scripts used to evaluate other watermarking methods under obfuscation attacks. 

For the remaining content, please refer to the usage instructions provided in the repositories of the other watermarking methods for reproduction.

