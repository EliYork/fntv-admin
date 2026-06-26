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
