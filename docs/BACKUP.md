# 备份

需要备份的正式数据都位于 `/data`。

建议备份：

```text
/data/admin.db
/data/logs
/data/cache
/data/backup
```

飞牛影视原始数据库不由本项目管理。`fntv-admin` 只读读取 `/fntv/trimmedia.db`，不会对它执行备份、迁移或写入操作。

## 恢复

1. 停止容器。
2. 恢复 `./data` 目录。
3. 确认飞牛数据库目录挂载到 `/fntv`，FNOS 实机默认不要追加 Docker 层 `:ro`。
4. 执行 `docker compose up -d`。
