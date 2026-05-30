# User Guide

## Environment Requirements

```bash
conda create -n myMetagpt -c conda-forge python=3.9 pip=24.1.2 -y
conda create -n myMetagpt python=3.9
```

### `Metagpt` Version:

> version: 0.8.2
>
> ```bash
> $ git log -1 --oneline
> df9bc185 (HEAD -> metagpt-0.8.2, tag: v0.8.2) Merge pull request #1732 from XiangJinyu/main
> ```

## Quick Start

### Clone the `git` repository:

```bash
git clone https://github.com/FoundationAgents/MetaGPT.git
```

### Switch branches:

```bash
# Change into the repository root
cd MetaGPT/
# Fetch all branches and tags
git fetch --all --tags
# Check whether the tag is v0.8.2 or 0.8.2 (the repo typically uses the v prefix)
git tag -l | grep -E '^v?0\.8\.2$'
# Checkout the tag
git checkout tags/v0.8.2 -b metagpt-0.8.2

# Verify
git describe --tags --always
git log -1 --oneline
```

### Modify the code:

Replace the relevant files inside the `./metagpt` folder at this path into the downloaded repository.

### Install:

#### Developer mode

Run this from the root of the `MetaGPT` repository:

```bash
pip install -e .
```

Done.