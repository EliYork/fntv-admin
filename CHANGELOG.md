# Changelog

## 0.1.0 - Unreleased

- 建立 Docker Compose-first 项目基础。
- 增加 FastAPI 后端、Vue 前端和单容器 Dockerfile。
- 增加飞牛数据库只读连接、启动检查和 admin.db 初始化。
- 增加登录权限、仪表盘、观看历史、用户管理、媒体库基础能力。
- 增加 GitHub Actions 自动构建并推送 GHCR 镜像。
- 默认 Docker Compose 部署改为拉取 GHCR 成品镜像，保留开发者本地构建 compose。
- 增加 Docker Hub 备用镜像发布和 `docker-compose.dockerhub.yml` 部署文件，GHCR 仍为默认镜像源。
- V1 禁用飞牛数据库 snapshot 快照机制，业务接口统一通过 SQLite 只读源库直连读取 `/fntv/trimmedia.db`。
- 增加 Phase 7A 报表中心基础统计，包含总览、播放趋势、活跃用户榜、热门媒体榜、媒体类型分布和分辨率分布。
- 报表接口在后端 SQL 层聚合飞牛影视只读源库数据，不写入飞牛数据库，不恢复 snapshot。
- 调整飞牛默认 Compose 数据库挂载为 `/usr/local/apps/@appdata/trim.media/database:/fntv`，记录 WAL/SHM 场景下 Docker 层 `:ro` 可能导致 `unable to open database file`；应用代码层仍使用 SQLite `mode=ro` 和 `PRAGMA query_only = ON` 保证只读。
