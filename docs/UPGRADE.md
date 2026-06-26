# 升级

升级前建议备份 `./data`。

```bash
docker compose down
docker compose pull
docker compose up -d
```

升级不会修改飞牛影视数据库。`admin.db` 的迁移由后端启动流程处理，所有增强数据继续保存在 `/data/admin.db`。

开发者本地构建测试才使用：

```bash
docker compose -f docker-compose.build.yml build
docker compose -f docker-compose.build.yml up -d
```

以上命令仅用于开发，不是官方生产部署方式。
