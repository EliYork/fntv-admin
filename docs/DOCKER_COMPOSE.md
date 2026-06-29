# Docker Compose 部署

`docker-compose.yml` 是 `fntv-admin` 唯一官方生产部署入口。

飞牛 NAS 默认推荐使用 GHCR 成品镜像，不推荐在飞牛本机 build。默认 `docker-compose.yml` 使用 GHCR `image` 拉取镜像。Docker Hub 仅作为 GHCR 下载较慢时的备用镜像源。

## 启动

```bash
docker compose up -d
```

访问：

```text
http://localhost:8080
```

## 必需挂载

```yaml
volumes:
  - /usr/local/apps/@appdata/fntv-admin/data:/data
  - /usr/local/apps/@appdata/trim.media/database:/fntv
```

飞牛影视数据库目录挂载到 `/fntv`，后台只读读取 `/fntv/trimmedia.db`。`/data` 必须读写挂载，用于保存 `admin.db`、日志、缓存和备份。

不要把飞牛影视数据库目录挂到 `/data`。

## 飞牛 SQLite WAL 挂载说明

飞牛影视实机可能使用 SQLite WAL 模式。Docker 层给数据库目录追加 `:ro` 时，SQLite 可能因为无法访问或维护 `-wal`、`-shm`、锁相关文件而报：

```text
unable to open database file
```

如果遇到这个错误，优先确认 Compose 使用默认挂载：

```yaml
- /usr/local/apps/@appdata/trim.media/database:/fntv
```

不要把默认挂载改回 `:/fntv:ro`。项目的只读保护在应用代码层完成，而不是依赖 Docker 层 `:ro`。

## 源库只读直连

V1 默认直接只读读取 `/fntv/trimmedia.db`，不生成 snapshot 快照。

后端使用 SQLite URI `mode=ro` 打开飞牛数据库，并设置 `PRAGMA query_only = ON`。不执行 checkpoint、vacuum，不删除或修改飞牛源库的 wal/shm 文件。

`/data` 仍用于保存 `admin.db`、日志、缓存和备份。不要把飞牛影视数据库目录挂到 `/data`。

如果飞牛 UI 中显示数据库目录不是只读挂载，项目代码层仍使用只读连接保护源库。`python scripts/verify_fntv_readonly.py` 必须通过。未来如需 snapshot，可作为 V2 优化另行实现。

## 镜像地址

默认镜像地址格式：

```text
ghcr.io/eliyork/fntv-admin:latest
```

备用 Docker Hub 镜像地址格式：

```text
docker.io/eliyork/fntv-admin:latest
```

如果 GHCR 下载较慢，可以使用 `docker-compose.dockerhub.yml`：

```bash
docker compose -f docker-compose.dockerhub.yml up -d
```

两个 compose 文件的挂载规则保持一致：

```text
/usr/local/apps/@appdata/fntv-admin/data -> /data 读写
/usr/local/apps/@appdata/trim.media/database -> /fntv
```

发布 Docker Hub 备用镜像需要在 GitHub Secrets 中配置：

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

`DOCKERHUB_TOKEN` 应使用 Docker Hub access token，不要使用 Docker Hub 明文密码。未配置时 GHCR 镜像发布不受影响。

## 单容器生产模型

生产镜像通过多阶段构建完成：

1. Node 阶段构建 Vue 静态文件。
2. Python 阶段安装后端依赖。
3. 将前端 `dist` 复制到 FastAPI 静态目录。
4. 最终只运行一个 `fntv-admin` 服务容器。

## 开发者本地构建

以下命令仅用于开发者本地测试，不是官方生产部署方式，也不是飞牛可视化部署默认路径：

```bash
docker compose -f docker-compose.build.yml build
docker compose -f docker-compose.build.yml up -d
```
