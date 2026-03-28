# Usage Guide

## Add a Submodule

First push the generated architecture sub-repository to the remote `github` repository.

Then add it as a submodule in this repository:

```bash
# Register the submodule in the standard way (`--force` can reuse an entry with the same name from `.gitmodules`)
git submodule add -f -b master https://github.com/Cruise-z/<repo>.git \
  VSCode/Python/CodeWM_AutoTest/1_Availability/DT/codeGen/MetaGPT/workspace/<project>/<language>/<repo>
```

After that, commit as usual.
