# ProWES protocol evaluator

This evaluator builds, tests, packages, and briefly run-checks generated Java,
Python, and C++ repositories in a controlled container. The Docker image and
its invocation are part of the RQ1 measurement protocol.

## Build the image

From this directory:

```bash
docker build -t prowes-protocol-evaluator ./docker
```

The image contains Maven/JDK 11, Python/pytest, GCC/CMake/CTest, Xvfb, and the
GUI/runtime libraries used by the project tasks.

## Docker

Start a reusable container:

```bash
docker run -d --name CodeWM-DT prowes-protocol-evaluator sleep infinity
```

Evaluate a project through the unified protocol:

```bash
docker cp /path/to/project CodeWM-DT:/workspace/project
docker exec CodeWM-DT /usr/local/bin/eval_protocol.sh /workspace/project
```

The protocol writes build, test, runtime, and packaged-artifact evidence below
the evaluated project's `DTResults/` directory.

Stop and remove the reusable container when it is no longer needed:

```bash
docker stop CodeWM-DT
docker rm CodeWM-DT
```

## Rootless Podman

Podman can run the same image without membership in a Docker group:

```bash
podman build -t prowes-protocol-evaluator ./docker
podman run -d --name CodeWM-DT prowes-protocol-evaluator sleep infinity
./test_podman.sh /path/to/project
```

`test_podman.sh` forwards the documented timeout, proxy, Maven, pip, and CMake
settings. Run `./test_podman.sh --help` or inspect the script for the exact
environment variables.

## Runtime interpretation

Build and test timeouts are failures. The short runtime check distinguishes a
normally long-running GUI/server program from an output-producing infinite
loop. CPU-only busy-loop detection is disabled by default to avoid
misclassifying render loops, but can be enabled explicitly with
`RUNTIME_ENABLE_CPU_BUSY_CHECK=1`.

For reproducible review, record the built image ID/digest and the container
engine version together with every result bundle.
