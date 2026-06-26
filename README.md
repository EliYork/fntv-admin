# fntv-admin

`fntv-admin` 是从零开发的飞牛影视增强管理后台。项目官方只支持 Docker Compose 部署，生产环境优先使用一个容器运行 FastAPI 后端和 Vue 构建后的静态前端。

核心边界：

- Docker Compose 是唯一官方部署入口。
- 飞牛影视数据库只读挂载到 `/fntv/trimmedia.db`。
- 所有增强数据写入 `/data/admin.db`。
- 所有可变数据都保存在 `/data`。
- 不提供裸机、PM2、手动 Nginx、宝塔或 systemd 生产部署方式。

## 快速开始

1. 复制环境变量示例：

```bash
cp .env.example .env
```

2. 编辑 `docker-compose.yml`，把飞牛影视数据库宿主机路径改成真实路径，并保留 `:ro`：

```yaml
services:
  fntv-admin:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: fntv-admin
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
      - /path/to/trimmedia.db:/fntv/trimmedia.db:ro
```

3. 启动：

```bash
docker compose build
docker compose up -d
```

4. 打开：

```text
http://localhost:8080
```

首次进入时创建管理员账号。管理员密码只会以 hash 形式写入 `/data/admin.db`。

## 数据持久化

容器内固定路径：

```text
/fntv/trimmedia.db    飞牛影视数据库，只读
/data/admin.db        fntv-admin 增强数据
/data/logs            运行日志
/data/cache           缓存
/data/backup          备份
```

只要 `./data` 保留，删除并重建容器不会丢失后台配置、备注、隐藏状态、审计和任务记录。

## 飞牛数据库只读保护

`docker-compose.yml` 必须包含：

```yaml
- /path/to/trimmedia.db:/fntv/trimmedia.db:ro
```

后端通过 SQLite URI `mode=ro` 打开飞牛数据库，并在连接上设置 `PRAGMA query_only = ON`。业务代码不提供任何飞牛数据库写入接口。

可用探测脚本检查数据库结构：

```bash
python scripts/inspect_fntv_db.py /path/to/trimmedia.db
```

该命令仅用于开发诊断，不是官方生产部署方式。

## 当前阶段

当前实现覆盖 Phase 0 到 Phase 6 的基础骨架：

- Docker Compose-first 项目结构。
- FastAPI 后端与 Vue 前端。
- 单容器生产 Dockerfile。
- 启动检查、健康检查、数据库状态。
- 首次管理员初始化、登录、退出、当前用户、修改密码。
- 仪表盘、观看历史、用户管理、媒体库基础 API 与页面。

飞牛数据库表结构不确定时，页面会显示空状态或数据库异常提示，不会导致应用崩溃。

