# Docker Compose 部署

`docker-compose.yml` 是 `fntv-admin` 唯一官方生产部署入口。

飞牛 NAS 默认推荐使用 Docker Hub 成品镜像，不推荐在飞牛本机 build。默认 `docker-compose.yml` 使用 Docker Hub `image` 拉取镜像，GHCR 作为备用镜像源。

## 启动

```bash
docker compose up -d
```

访问：

```text
http://localhost:8080
```

推荐 Compose 示例：

```yaml
services:
  fntv-admin:
    image: docker.io/eliyork/fntv-admin:latest
    container_name: fntv-admin
    restart: unless-stopped

    ports:
      - "8080:8080"

    volumes:
      - /vol1/Docker/fntv-admin/data:/data
      - /usr/local/apps/@appdata/trim.media/database:/fntv

    environment:
      APP_ENV: production
      APP_SECRET_KEY: change-this-to-a-long-random-string

      FNTV_DB_PATH: /fntv/trimmedia.db
      ADMIN_DB_PATH: /data/admin.db
      LOG_DIR: /data/logs
      CACHE_DIR: /data/cache
      BACKUP_DIR: /data/backup
      DEFAULT_PAGE_SIZE: "20"
      LOG_RETENTION_DAYS: "14"
      SNAPSHOT_ENABLED: "false"
      ACTIVE_WATCH_WINDOW_SECONDS: "300"
```

`APP_SECRET_KEY` 必须在部署前改成足够长的随机字符串。

## 必需挂载

```yaml
volumes:
  - /vol1/Docker/fntv-admin/data:/data
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

## 源库只读直连与可选快照

默认直接只读读取 `/fntv/trimmedia.db`，`SNAPSHOT_ENABLED=false`。

后端使用 SQLite URI `mode=ro` 打开飞牛数据库，并设置 `PRAGMA query_only = ON`。不执行 checkpoint、vacuum，不删除或修改飞牛源库的 wal/shm 文件。

`/data` 仍用于保存 `admin.db`、日志、缓存和备份。不要把飞牛影视数据库目录挂到 `/data`。

如果飞牛 UI 中显示数据库目录不是只读挂载，项目代码层仍使用只读连接保护源库。`python scripts/verify_fntv_readonly.py` 必须通过。

可选快照读取可以通过环境变量或系统设置开启。开启后，应用会尝试用 SQLite backup API 生成 `/data/cache/trimmedia.snapshot.db`。快照成功时业务查询优先读取快照；快照失败时自动回退源库只读直连，页面不应白屏。快照只写 `/data/cache`，不写飞牛源库，不复制 `.wal/.shm` 作为主要方案。

## 访问控制

默认策略保持安全：

```text
本地访问：需要登录
外部访问：需要登录
TRUST_PROXY_HEADERS=false
```

系统设置页可以切换为“本地免登录 + 外部需要登录”，适合仅在可信飞牛内网自用的环境。外部访问也可以设置为“禁止访问”，非本地来源会直接返回 403。

本地来源包括 `127.0.0.1`、`::1`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`fc00::/7`、`fe80::/10`。默认不信任 `X-Forwarded-For` / `X-Real-IP`。如果部署在反向代理后，只有确认代理会覆盖并清理这些请求头时，才设置：

```env
TRUST_PROXY_HEADERS=true
```

公网、DDNS 或反向代理访问建议保持外部访问需要登录，或直接禁止外部访问。

## 镜像地址

默认 Docker Hub 镜像地址：

```text
docker.io/eliyork/fntv-admin:latest
docker.io/eliyork/fntv-admin:v0.7.2
```

备用 GHCR 镜像地址：

```text
ghcr.io/eliyork/fntv-admin:latest
ghcr.io/eliyork/fntv-admin:v0.7.2
```

默认 Compose 的挂载规则：

```text
/vol1/Docker/fntv-admin/data -> /data 读写
/usr/local/apps/@appdata/trim.media/database -> /fntv
```

发布 Docker Hub 镜像需要在 GitHub Secrets 中配置：

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

`DOCKERHUB_TOKEN` 应使用 Docker Hub access token，不要使用 Docker Hub 明文密码。

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
