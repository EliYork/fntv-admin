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
  - /usr/local/apps/@appdata/trim.media/database:/fntv:ro
```

飞牛影视数据库目录挂载必须保留 `:ro`，后台只读读取 `/fntv/trimmedia.db`。`/data` 必须读写挂载，用于保存 `admin.db`、日志、缓存和备份。

不要把飞牛影视数据库目录挂到 `/data`，也不要读写挂载飞牛影视数据库目录。

## 快照机制

飞牛数据库可能处于 SQLite WAL 模式，直接以只读方式打开原库时可能因为 `-wal`、`-shm` 文件或目录权限问题导致失败。fntv-admin 使用 SQLite backup API 生成一致性快照解决此问题：

1. 启动时以只读方式打开源库，使用 `sqlite3.Connection.backup()` 生成单文件快照到 `/data/cache/trimmedia.snapshot.db`。
2. 快照经过 `PRAGMA quick_check` 校验后原子替换。
3. 所有业务查询和 schema 探测读取快照库。
4. 不写入源库，不 checkpoint 源库，不删除源库 wal/shm。
5. 系统设置页可以手动刷新快照。
6. 快照不可用时自动降级为源库只读直连。

`/data` 必须读写挂载才能保存快照文件。`/fntv` 应尽量只读挂载；即使飞牛 UI 显示读写，后端仍然只读读取源库。

## 镜像地址

默认镜像地址格式：

```text
ghcr.io/<GitHub用户名>/fntv-admin:latest
```

使用前把 `docker-compose.yml` 中的 `REPLACE_WITH_YOUR_GITHUB_USERNAME` 替换为自己的 GitHub 用户名或组织名。

备用 Docker Hub 镜像地址格式：

```text
docker.io/<DockerHub用户名>/fntv-admin:latest
```

如果 GHCR 下载较慢，可以使用 `docker-compose.dockerhub.yml`：

```bash
docker compose -f docker-compose.dockerhub.yml up -d
```

使用前把 `docker-compose.dockerhub.yml` 中的 `REPLACE_WITH_YOUR_DOCKERHUB_USERNAME` 替换为自己的 Docker Hub 用户名。

两个 compose 文件的挂载规则保持一致：

```text
/usr/local/apps/@appdata/fntv-admin/data -> /data 读写
/usr/local/apps/@appdata/trim.media/database -> /fntv 只读
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
