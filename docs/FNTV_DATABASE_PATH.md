# 飞牛数据库路径说明

飞牛影视数据库在容器内固定为：

```text
/fntv/trimmedia.db
```

飞牛 NAS 推荐把数据库目录只读挂载到 `/fntv`：

```yaml
- /usr/local/apps/@appdata/trim.media/database:/fntv:ro
```

`fntv-admin` 不会在代码中写宿主机路径，也不会写入飞牛影视数据库。

`fntv-admin` 自己的数据目录推荐读写挂载：

```yaml
- /usr/local/apps/@appdata/fntv-admin/data:/data
```

不要把飞牛影视数据库目录挂到 `/data`。

## 只读要求

必须满足：

- Docker Compose 挂载使用 `:ro`。
- 后端使用 SQLite `mode=ro` 打开。
- 后端连接启用 `PRAGMA query_only = ON`。
- 增强数据只写入 `/data/admin.db`。
