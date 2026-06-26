# 升级

升级前建议备份 `./data`。

```bash
docker compose down
docker compose build
docker compose up -d
```

升级不会修改飞牛影视数据库。`admin.db` 的迁移由后端启动流程处理，所有增强数据继续保存在 `/data/admin.db`。

