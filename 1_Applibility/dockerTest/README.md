# README

## Usage Guide

### Docker image operations

#### Build and run the image

##### Change to the Dockerfile directory

`cd Docker`

##### Build the image

`docker build -t codewm_dt_docker:11 .`

##### Start a long-lived reusable container

`docker run -d --name CodeWM-DT codewm_dt_docker:11`

#### Remove an image

##### Stop and remove the container first

`docker ps -a`
`docker stop 39866e136289`
`docker rm 39866e136289`

##### Then remove the image

`docker images`
`docker image rm maven-only:11`

#### Opening and closing containers
##### Start

`docker start 6a308cffe308`

##### Stop

`docker stop 6a308cffe308`


#### Code testing
##### Build code dependencies
Run: `python ./1_Availability/DT/dockerTest/autoConfig.py --filepath [CodePath]`
##### Run docker test
Run: `./1_Availability/DT/dockerTest/test.sh [CodePath]`
Example:
`./1_Availability/DT/dockerTest/test.sh /home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/results/stdDemo/SnakeGame/SnakeGame.java`

#### Tips
It is recommended to remove the previous container before rerunning tests. Use:
`docker ps -a`
`docker rm [container ID to remove]`
`docker run -d --name CodeWM-DT codewm_dt_docker:11`
Then rerun the test.

### Run Docker images with podman

You can use `podman` to build and run the image without root privileges or the docker user group.
Podman is designed to be CLI-compatible with Docker, so these commands can be used as direct replacements:
| Docker 命令                   | Podman 对应命令                 | 是否兼容   |
| --------------------------- | --------------------------- | ------ |
| `docker build -t myimg .`   | `podman build -t myimg .`   | ✅ 完全兼容 |
| `docker run -it myimg bash` | `podman run -it myimg bash` | ✅ 完全兼容 |
| `docker ps`                 | `podman ps`                 | ✅ 完全兼容 |
| `docker images`             | `podman images`             | ✅ 完全兼容 |
| `docker rm <id>`            | `podman rm <id>`            | ✅ 完全兼容 |
| `docker rmi <id>`           | `podman rmi <id>`           | ✅ 完全兼容 |
| `docker exec -it <id> bash` | `podman exec -it <id> bash` | ✅ 完全兼容 |
| `docker logs <id>`          | `podman logs <id>`          | ✅ 完全兼容 |

When using this in the terminal, you can run:
`alias docker=podman`
This way all Docker commands become Podman commands.

##### Build the image

`podman build --format docker -t codewm_dt_docker:proWES .`

##### Start a long-lived reusable container

`podman run -d --network=host --name CodeWM-DT codewm_dt_docker:proWES`
`podman run -d --network=host --name CodeWM-DT codewm_dt_docker:proWES sleep infinity`

Enter the container shell:
`podman run -it --rm codewm_dt_docker:proWES /bin/bash`

#### 删除镜像

##### 先停止并删除容器

`podman ps -a`
`podman stop 39866e136289`
`podman rm 39866e136289`

##### 再删除镜像

`podman images`
`podman image rm maven-only:11`

#### Code testing
##### Build code dependencies
Run: `python ./1_Availability/DT/dockerTest/autoConfig.py --filepath [CodePath]`
##### Run podman test
Run: `./1_Availability/DT/dockerTest/test_podman.sh [CodePath]`
Example:
`./1_Availability/DT/dockerTest/test_podman.sh /home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/results/stdDemo/SnakeGame/SnakeGame.java`