# 升级

升级前建议备份 `./data`。

```bash
docker compose down
docker compose pull
docker compose up -d
```

默认镜像源为 Docker Hub：

```text
docker.io/eliyork/fntv-admin:latest
docker.io/eliyork/fntv-admin:v0.7.2
```

备用 GHCR 镜像：

```text
ghcr.io/eliyork/fntv-admin:latest
ghcr.io/eliyork/fntv-admin:v0.7.2
```

升级不会修改飞牛影视数据库。`admin.db` 的迁移由后端启动流程处理，所有增强数据继续保存在 `/data/admin.db`。

开发者本地构建测试才使用：

```bash
docker compose -f docker-compose.build.yml build
docker compose -f docker-compose.build.yml up -d
```

以上命令仅用于开发，不是官方生产部署方式。
