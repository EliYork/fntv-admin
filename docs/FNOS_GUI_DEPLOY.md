# 飞牛可视化部署

飞牛 NAS 默认推荐使用 GHCR 成品镜像部署 `fntv-admin`，不要在飞牛本机 build 镜像。若 GHCR 下载较慢，可以切换到 Docker Hub 备用镜像。

原因：

- 飞牛本机构建时可能需要拉取 `docker.io/library/node:22-alpine` 和 `docker.io/library/python:3.12-slim`。
- 这些基础镜像在部分网络环境下容易超时。
- GitHub Actions 可以在云端完成多阶段构建，并把最终单容器镜像推送到 GHCR。
- 配置 Docker Hub secrets 后，同一 workflow 也会发布 Docker Hub 备用镜像。

## 部署方式 A：导入 Compose / 项目 / 应用栈

在飞牛 Docker 可视化界面中选择 Compose、项目或应用栈导入，把项目的 `docker-compose.yml` 内容粘贴进去。

默认部署前必须修改 GHCR 镜像名：

```yaml
image: ghcr.io/eliyork/fntv-admin:latest
```

如果 GHCR 下载慢，可以改用 `docker-compose.dockerhub.yml`，并修改 Docker Hub 镜像名：

```yaml
image: docker.io/<DockerHub用户名>/fntv-admin:latest
```

端口：

```text
宿主机 8080 -> 容器 8080
```

挂载：

```text
/usr/local/apps/@appdata/fntv-admin/data -> /data，读写
/usr/local/apps/@appdata/trim.media/database -> /fntv
```

飞牛数据库挂载默认不要追加 Docker 层 `:ro`：

```yaml
- /usr/local/apps/@appdata/trim.media/database:/fntv
```

`/data` 必须读写挂载，否则 `admin.db`、日志、缓存无法持久化。不要把飞牛影视数据库目录挂到 `/data`。

飞牛影视实机可能使用 SQLite WAL 模式。如果 Docker 层把数据库目录设为只读，SQLite 可能因为无法访问或维护 `-wal`、`-shm`、锁相关文件而报 `unable to open database file`。出现这个错误时，先去掉 `/fntv` 挂载末尾的 `:ro`。

环境变量：

```env
APP_ENV=production
APP_SECRET_KEY=change-me-please
FNTV_DB_PATH=/fntv/trimmedia.db
ADMIN_DB_PATH=/data/admin.db
LOG_DIR=/data/logs
CACHE_DIR=/data/cache
BACKUP_DIR=/data/backup
DEFAULT_PAGE_SIZE=20
LOG_RETENTION_DAYS=14
```

启动后访问：

```text
http://飞牛IP:8080
```

首次进入需要初始化管理员账号。

## 部署方式 B：先拉取镜像再创建容器

在飞牛 Docker 镜像页面拉取：

```text
ghcr.io/eliyork/fntv-admin:latest
```

如果 GHCR 下载慢，可以改拉 Docker Hub 备用镜像：

```text
docker.io/eliyork/fntv-admin:latest
```

然后创建容器：

- 容器端口：`8080`
- 宿主机端口：`8080`
- 挂载 `/usr/local/apps/@appdata/fntv-admin/data` 到 `/data`，读写
- 挂载 `/usr/local/apps/@appdata/trim.media/database` 到 `/fntv`
- 设置上方环境变量

这种方式适合不使用 Compose 导入的飞牛环境。长期维护仍推荐使用 Compose / 项目 / 应用栈方式。

## 镜像拉取失败

如果 GHCR 镜像拉取失败，请检查：

1. GitHub Packages 中的 `fntv-admin` package 是否为 public。
2. 飞牛 NAS 是否能访问 `ghcr.io`。
3. 如果 package 是 private，需要在飞牛 Docker 中登录 GHCR。

如果 GHCR 在当前网络下下载较慢，可以使用 Docker Hub 备用镜像：

```text
docker.io/eliyork/fntv-admin:latest
```

发布 Docker Hub 镜像需要在 GitHub Secrets 中配置：

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

`DOCKERHUB_TOKEN` 应使用 Docker Hub access token，不要使用 Docker Hub 明文密码。未配置这两个 secrets 时，GHCR 发布仍会正常运行，只是 Docker Hub 发布步骤会跳过。

## 数据库安全提醒

不要把飞牛影视数据库目录挂到 `/data`。飞牛默认部署不再要求 Docker 层 `:ro`，因为 WAL/SHM 场景下 `:ro` 可能导致 SQLite 无法打开数据库。

正确方式：

```yaml
- /usr/local/apps/@appdata/trim.media/database:/fntv
```

fntv-admin V1 直接只读读取 `/fntv/trimmedia.db`，不生成 snapshot 快照。后端使用 SQLite `mode=ro` 和 `PRAGMA query_only = ON` 保护源库，不写入源库、不 checkpoint 源库、不删除或修改源库 wal/shm 文件。部署后应确认 `python scripts/verify_fntv_readonly.py` 通过。

如果数据库状态异常，优先检查：

1. `/usr/local/apps/@appdata/fntv-admin/data` 是否读写挂载到 `/data`。
2. `/usr/local/apps/@appdata/trim.media/database` 是否挂载到 `/fntv`，且飞牛实机下没有强制追加 `:ro`。
3. `FNTV_DB_PATH` 是否仍为 `/fntv/trimmedia.db`。
4. 系统设置页查看源库只读直连状态和 schema 诊断。

如果不确定路径或担心影响原始数据，可以先复制一份 `trimmedia.db` 到 `test-db` 目录，用测试副本验证页面和数据库状态。

## 只读连接成功但结构读取失败

如果系统设置页显示"只读连接：是"但数据库状态为异常，说明：

1. 飞牛数据库挂载大概率是成功的。
2. 后端可以只读打开数据库文件。
3. 问题出在飞牛数据库的表结构与 fntv-admin 适配器不完全匹配。

处理步骤：

1. 进入系统设置页，查看"飞牛数据库诊断"区域。
2. 确认"检测到的表数量"是否大于 0。
3. 查看"核心表匹配状态"和"功能支持"区域。
4. 点击"复制诊断信息"按钮，将脱敏 JSON 信息提交给开发者。

不要做的事：

1. 不要反复修改 Docker Compose 挂载路径。
2. 不要删除 `/data` 目录重新初始化。
3. 不要绕过应用代码层只读保护。

该问题通常是飞牛影视版本升级后数据库字段发生了变化，需要在 fntv-admin 中做适配。诊断信息可以帮助开发者快速定位缺失的表或字段。
