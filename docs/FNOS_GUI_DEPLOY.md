# 飞牛可视化部署

飞牛 NAS 推荐使用 GHCR 成品镜像部署 `fntv-admin`，不要在飞牛本机 build 镜像。

原因：

- 飞牛本机构建时可能需要拉取 `docker.io/library/node:22-alpine` 和 `docker.io/library/python:3.12-slim`。
- 这些基础镜像在部分网络环境下容易超时。
- GitHub Actions 可以在云端完成多阶段构建，并把最终单容器镜像推送到 GHCR。

## 部署方式 A：导入 Compose / 项目 / 应用栈

在飞牛 Docker 可视化界面中选择 Compose、项目或应用栈导入，把项目的 `docker-compose.yml` 内容粘贴进去。

部署前必须修改：

```yaml
image: ghcr.io/<用户名>/fntv-admin:latest
```

把 `<用户名>` 改成 GitHub 用户名或组织名。

端口：

```text
宿主机 8080 -> 容器 8080
```

挂载：

```text
./data 或飞牛某个目录 -> /data
trimmedia.db -> /fntv/trimmedia.db，只读
```

飞牛数据库挂载必须是只读：

```yaml
- /path/to/trimmedia.db:/fntv/trimmedia.db:ro
```

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
ghcr.io/<用户名>/fntv-admin:latest
```

然后创建容器：

- 容器端口：`8080`
- 宿主机端口：`8080`
- 挂载数据目录到 `/data`
- 挂载 `trimmedia.db` 到 `/fntv/trimmedia.db`，并设置为只读
- 设置上方环境变量

这种方式适合不使用 Compose 导入的飞牛环境。长期维护仍推荐使用 Compose / 项目 / 应用栈方式。

## 镜像拉取失败

如果 GHCR 镜像拉取失败，请检查：

1. GitHub Packages 中的 `fntv-admin` package 是否为 public。
2. 飞牛 NAS 是否能访问 `ghcr.io`。
3. 如果 package 是 private，需要在飞牛 Docker 中登录 GHCR。

本项目不需要 Docker Hub secrets，也不要求飞牛本机 build。

## 数据库安全提醒

不要把飞牛影视数据库以读写方式挂载。

正确方式：

```yaml
- /path/to/trimmedia.db:/fntv/trimmedia.db:ro
```

如果不确定路径或担心影响原始数据，可以先复制一份 `trimmedia.db` 到 `test-db` 目录，用测试副本验证页面和数据库状态。
