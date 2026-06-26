# fntv-admin

`fntv-admin` 是从零开发的飞牛影视增强管理后台。项目官方只支持 Docker Compose 部署，生产环境优先使用一个容器运行 FastAPI 后端和 Vue 构建后的静态前端。

飞牛 NAS 默认推荐直接拉取 GitHub Container Registry（GHCR）成品镜像运行，不推荐在飞牛本机 build 镜像。若 GHCR 在当前网络下下载较慢，可以切换到 Docker Hub 备用镜像。

核心边界：

- Docker Compose 是唯一官方部署入口。
- 默认部署使用 GHCR 成品镜像。
- Docker Hub 仅作为备用镜像源。
- 飞牛影视数据库只读挂载到 `/fntv/trimmedia.db`。
- 所有增强数据写入 `/data/admin.db`。
- 所有可变数据都保存在 `/data`。
- 不提供裸机、PM2、手动 Nginx、宝塔或 systemd 生产部署方式。

## 快速开始

1. 复制 `docker-compose.yml` 到飞牛 NAS 的应用目录。

2. 修改镜像地址，把 `REPLACE_WITH_YOUR_GITHUB_USERNAME` 改成 GitHub 用户名或组织名：

```yaml
services:
  fntv-admin:
    image: ghcr.io/REPLACE_WITH_YOUR_GITHUB_USERNAME/fntv-admin:latest
    container_name: fntv-admin
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /usr/local/apps/@appdata/fntv-admin/data:/data
      - /usr/local/apps/@appdata/trim.media/database:/fntv:ro
    environment:
      APP_ENV: production
      APP_SECRET_KEY: change-me-please
      FNTV_DB_PATH: /fntv/trimmedia.db
      ADMIN_DB_PATH: /data/admin.db
      LOG_DIR: /data/logs
      CACHE_DIR: /data/cache
      BACKUP_DIR: /data/backup
      DEFAULT_PAGE_SIZE: "20"
      LOG_RETENTION_DAYS: "14"
```

如果 GHCR 下载较慢，可以改用 `docker-compose.dockerhub.yml`，并把 `REPLACE_WITH_YOUR_DOCKERHUB_USERNAME` 改成 Docker Hub 用户名：

```yaml
image: docker.io/REPLACE_WITH_YOUR_DOCKERHUB_USERNAME/fntv-admin:latest
```

3. 检查挂载路径：

```text
飞牛影视数据库目录：/usr/local/apps/@appdata/trim.media/database -> /fntv 只读
fntv-admin 数据目录：/usr/local/apps/@appdata/fntv-admin/data -> /data 读写
```

`FNTV_DB_PATH` 保持 `/fntv/trimmedia.db`。不要把飞牛影视数据库目录挂到 `/data`，也不要读写挂载飞牛影视数据库目录。

4. 启动：

```bash
docker compose up -d
```

5. 打开：

```text
http://localhost:8080
```

在飞牛 NAS 上访问时，把 `localhost` 换成飞牛 IP：

```text
http://飞牛IP:8080
```

首次进入时创建管理员账号。管理员密码只会以 hash 形式写入 `/data/admin.db`。

## GHCR 镜像

GitHub Actions 会在以下场景构建并推送镜像到 GHCR：

- push 到 `main` 分支。
- push `v*.*.*` 版本 tag。
- 手动触发 `workflow_dispatch`。

镜像名格式：

```text
ghcr.io/<GitHub用户名>/fntv-admin:latest
ghcr.io/<GitHub用户名>/fntv-admin:sha-<git-sha>
ghcr.io/<GitHub用户名>/fntv-admin:<tag>
```

如果仓库默认分支不是 `main`，需要在 `.github/workflows/docker-image.yml` 中把触发分支改成实际默认分支。

## Docker Hub 备用镜像

GHCR 仍然是默认镜像源。Docker Hub 只作为 GHCR 下载较慢时的备用镜像源：

```text
docker.io/<DockerHub用户名>/fntv-admin:latest
docker.io/<DockerHub用户名>/fntv-admin:sha-<git-sha>
docker.io/<DockerHub用户名>/fntv-admin:<tag>
```

如需让 GitHub Actions 同步发布 Docker Hub 镜像，请在仓库的 GitHub Secrets 中配置：

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

`DOCKERHUB_TOKEN` 应使用 Docker Hub access token，不要使用 Docker Hub 明文密码。未配置这两个 secrets 时，workflow 只发布 GHCR 镜像，Docker Hub 步骤会跳过。

飞牛 NAS 上如果 GHCR 下载慢，可以导入 `docker-compose.dockerhub.yml`，并把镜像名改成：

```text
docker.io/<DockerHub用户名>/fntv-admin:latest
```

## 数据持久化

容器内固定路径：

```text
/fntv/trimmedia.db                飞牛影视数据库，只读，由 /fntv 目录挂载提供
/data/cache/trimmedia.snapshot.db 快照库，启动时从源库复制，业务查询读取此文件
/data/admin.db                    fntv-admin 增强数据
/data/logs                        运行日志
/data/cache                       缓存
/data/backup                      备份
```

只要 `./data` 保留，删除并重建容器不会丢失后台配置、备注、隐藏状态、审计和任务记录。

## 飞牛数据库只读保护

`docker-compose.yml` 推荐包含：

```yaml
- /usr/local/apps/@appdata/trim.media/database:/fntv:ro
```

`/data` 必须读写挂载，否则 `admin.db`、日志和缓存无法持久化。`/fntv` 必须只读挂载。后端通过 SQLite URI `mode=ro` 打开飞牛数据库，并在连接上设置 `PRAGMA query_only = ON`。业务代码不提供任何飞牛数据库写入接口。

## 快照机制

飞牛数据库可能处于 SQLite WAL 模式，直接以只读方式打开原库时可能因为 `-wal`、`-shm` 文件或目录权限问题导致 `unable to open database file`。

fntv-admin 使用快照机制解决此问题：

1. 启动时将 `/fntv/trimmedia.db`（以及 `.db-wal`、`.db-shm`）复制到 `/data/cache/trimmedia.snapshot.db`。
2. 所有业务查询和 schema 探测读取的是快照库，而非直接读取源库。
3. 快照通过临时文件 + 原子替换生成，避免半写文件被查询。
4. 源库始终保持只读，不会被修改。
5. 系统设置页可以手动刷新快照。

容器内路径：

```text
/fntv/trimmedia.db               源数据库，只读
/data/cache/trimmedia.snapshot.db 快照库，只读查询
/data/admin.db                    增强数据
/data/logs                        运行日志
/data/cache                       缓存
/data/backup                      备份
```

只要 `./data` 保留，删除并重建容器不会丢失后台配置、备注、隐藏状态、审计和任务记录。

## 开发者本地构建

以下命令仅用于开发者本地测试，不是官方生产部署方式，也不是飞牛可视化部署默认路径：

```bash
docker compose -f docker-compose.build.yml build
docker compose -f docker-compose.build.yml up -d
```

## 飞牛可视化部署

飞牛 Docker 可视化界面部署步骤见 [docs/FNOS_GUI_DEPLOY.md](docs/FNOS_GUI_DEPLOY.md)。

## 当前阶段

当前实现覆盖 Phase 0 到 Phase 6 的基础骨架：

- Docker Compose-first 项目结构。
- FastAPI 后端与 Vue 前端。
- 单容器生产 Dockerfile。
- GHCR 自动构建发布 workflow，Docker Hub 作为可选备用发布目标。
- 启动检查、健康检查、数据库状态。
- 首次管理员初始化、登录、退出、当前用户、修改密码。
- 仪表盘、观看历史、用户管理、媒体库基础 API 与页面。

飞牛数据库表结构不确定时，页面会显示空状态或数据库异常提示，不会导致应用崩溃。
