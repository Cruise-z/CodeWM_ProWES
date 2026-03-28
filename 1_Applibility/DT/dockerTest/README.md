# README

## Usage Guide

### `Docker` Image Operations

#### Build and Run the Image

##### Go to the directory containing the Dockerfile

`cd Docker`

##### Build the image

`docker build -t codewm_dt_docker:11 .`

##### Start a long-running reusable container

`docker run -d --name CodeWM-DT codewm_dt_docker:11`

#### Remove the image

##### First stop and remove the container

`docker ps -a`
`docker stop 39866e136289`
`docker rm 39866e136289`

##### Then remove the image

`docker images`
`docker image rm maven-only:11`

#### Start and Stop the Container
##### Start

`docker start 6a308cffe308`

##### Stop

`docker stop 6a308cffe308`


#### Code Testing
##### Build code dependencies
Run: `python ./1_Availability/DT/dockerTest/autoConfig.py --filepath [CodePath]`
##### Run the `docker` test
Run: `./1_Availability/DT/dockerTest/test.sh [CodePath]`
e.g:
`./1_Availability/DT/dockerTest/test.sh /home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/results/stdDemo/SnakeGame/SnakeGame.java`

#### Tips: 
When you stop the Docker container and want to test again, it is recommended to remove the previous container and recreate it:
`docker ps -a`
`docker rm [container-id-to-remove]`
`docker run -d --name CodeWM-DT codewm_dt_docker:11`
Then run the test again.

### Run the `Docker` Image with `podman`

With `podman`, you can build and run the image without root privileges or membership in the Docker user group.
Podman is designed to be Docker CLI compatible, so these commands can be used as direct replacements:
| Docker Command             | Podman Equivalent            | Compatibility |
| --------------------------- | --------------------------- | ------ |
| `docker build -t myimg .`   | `podman build -t myimg .`   | Fully compatible |
| `docker run -it myimg bash` | `podman run -it myimg bash` | Fully compatible |
| `docker ps`                 | `podman ps`                 | Fully compatible |
| `docker images`             | `podman images`             | Fully compatible |
| `docker rm <id>`            | `podman rm <id>`            | Fully compatible |
| `docker rmi <id>`           | `podman rmi <id>`           | Fully compatible |
| `docker exec -it <id> bash` | `podman exec -it <id> bash` | Fully compatible |
| `docker logs <id>`          | `podman logs <id>`          | Fully compatible |

In the terminal, you can run:
`alias docker=podman`
This effectively turns all Docker commands into Podman commands.

##### Build the image

`podman build --format docker -t codewm_dt_docker:11 .`

##### Start a long-running reusable container

`podman run -d --network=host --name CodeWM-DT codewm_dt_docker:11`
`podman run -d --network=host --name CodeWM-DT codewm_dt_docker:11 sleep infinity`

Open a shell inside the container:
`podman run -it --rm codewm_dt_docker:11 /bin/bash`

#### Remove the image

##### First stop and remove the container

`podman ps -a`
`podman stop 39866e136289`
`podman rm 39866e136289`

##### Then remove the image

`podman images`
`podman image rm maven-only:11`

#### Code Testing
##### Build code dependencies
Run: `python ./1_Availability/DT/dockerTest/autoConfig.py --filepath [CodePath]`
##### Run the `docker` test
Run: `./1_Availability/DT/dockerTest/test_podman.sh [CodePath]`
e.g:
`./1_Availability/DT/dockerTest/test_podman.sh /home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/results/stdDemo/SnakeGame/SnakeGame.java`
