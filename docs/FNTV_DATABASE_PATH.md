# 飞牛数据库路径说明

飞牛影视数据库在容器内固定为：

```text
/fntv/trimmedia.db
```

飞牛 NAS 推荐把数据库目录挂载到 `/fntv`，不要在 FNOS 实机默认部署中追加 Docker 层 `:ro`：

```yaml
- /usr/local/apps/@appdata/trim.media/database:/fntv
```

飞牛影视实机可能使用 SQLite WAL 模式。Docker 层强制只读可能阻止 SQLite 访问或维护 `-wal`、`-shm`、锁相关文件，导致 `unable to open database file`。这不代表应用会写飞牛数据库；只读边界由应用代码层保证。

`fntv-admin` 不会在代码中写宿主机路径，也不会写入飞牛影视数据库。

`fntv-admin` 自己的数据目录推荐读写挂载：

```yaml
- /vol1/Docker/fntv-admin/data:/data
```

不要把飞牛影视数据库目录挂到 `/data`。

## 只读要求

必须满足：

- Docker Compose 默认把 `/usr/local/apps/@appdata/trim.media/database` 挂载到 `/fntv`，FNOS / WAL / SHM 场景下不强制 `:ro`。
- 后端使用 SQLite `mode=ro` 打开。
- 后端连接启用 `PRAGMA query_only = ON`。
- `python scripts/verify_fntv_readonly.py` 验证没有飞牛数据库写入路径。
- 增强数据只写入 `/data/admin.db`。
