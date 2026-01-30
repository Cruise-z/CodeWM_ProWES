# README

## 操作文档

### `Docker`镜像操作

#### 构建并运行镜像

##### 进入 Dockerfile 所在目录

`cd Docker`

##### 构建镜像

`docker build -t codewm_dt_docker:11 .`

##### 启动一个长期可复用的容器

`docker run -d --name CodeWM-DT codewm_dt_docker:11`

#### 删除镜像

##### 先停止并删除容器

`docker ps -a`
`docker stop 39866e136289`
`docker rm 39866e136289`

##### 再删除镜像

`docker images`
`docker image rm maven-only:11`

#### 容器的打开与关闭
##### 打开

`docker start 6a308cffe308`

##### 关闭

`docker stop 6a308cffe308`


#### 代码测试
##### 构建代码依赖
执行：`python ./1_Availability/DT/dockerTest/autoConfig.py --filepath [CodePath]`命令
##### 进行`docker`测试
执行：`./1_Availability/DT/dockerTest/test.sh [CodePath]`命令
e.g:
`./1_Availability/DT/dockerTest/test.sh /home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/results/stdDemo/SnakeGame/SnakeGame.java`

#### Tips: 
建议每次关掉docker容器重新进行测试时，将上次使用的容器删除，重新执行如下操作：
`docker ps -a`
`docker rm [你要删除的容器ID]`
`docker run -d --name CodeWM-DT codewm_dt_docker:11`
然后再进行测试

### 使用`podman`运行`Docker`镜像

使用`podman`可以在没有root权限和docker用户组的情况下构建并运行镜像
Podman 专门设计成 Docker CLI 兼容，这些命令都能直接替换使用：
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

在终端中使用时，可以执行：
`alias docker=podman`
这样所有 Docker 命令都“变成”了 Podman 命令。

##### 构建镜像

`podman build --format docker -t codewm_dt_docker:11 .`

##### 启动一个长期可复用的容器

`podman run -d --network=host --name CodeWM-DT codewm_dt_docker:11`
`podman run -d --network=host --name CodeWM-DT codewm_dt_docker:11 sleep infinity`

进入容器终端：
`podman run -it --rm codewm_dt_docker:11 /bin/bash`

#### 删除镜像

##### 先停止并删除容器

`podman ps -a`
`podman stop 39866e136289`
`podman rm 39866e136289`

##### 再删除镜像

`podman images`
`podman image rm maven-only:11`

#### 代码测试
##### 构建代码依赖
执行：`python ./1_Availability/DT/dockerTest/autoConfig.py --filepath [CodePath]`命令
##### 进行`docker`测试
执行：`./1_Availability/DT/dockerTest/test_podman.sh [CodePath]`命令
e.g:
`./1_Availability/DT/dockerTest/test_podman.sh /home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/results/stdDemo/SnakeGame/SnakeGame.java`