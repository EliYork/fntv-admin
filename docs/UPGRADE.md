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
docker.io/eliyork/fntv-admin:vX.Y.Z
```

备用 GHCR 镜像：

```text
ghcr.io/eliyork/fntv-admin:latest
ghcr.io/eliyork/fntv-admin:vX.Y.Z
```

仓库中的 `docker-compose.yml` 始终跟随 `latest`。需要锁定正式版本时，从对应 GitHub Release 下载 `fntv-admin-vX.Y.Z.yml` 并核对同一 Release 中的 `SHA256SUMS.txt`。

升级不会修改飞牛影视数据库。`admin.db` 的迁移由后端启动流程处理，所有增强数据继续保存在 `/data/admin.db`。

Phase 7C 增加可选快照读取、播放时段分布、最近活跃观看推断、收藏/下载只读能力、历史时间筛选和增强 CSV。快照默认关闭；开启后只写 `/data/cache/trimmedia.snapshot.db`，失败时回退源库只读直连。

开发者本地构建测试才使用：

```bash
docker compose -f docker-compose.build.yml build
docker compose -f docker-compose.build.yml up -d
```

以上命令仅用于开发，不是官方生产部署方式。
