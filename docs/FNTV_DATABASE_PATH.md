# 飞牛数据库路径说明

飞牛影视数据库在容器内固定为：

```text
/fntv/trimmedia.db
```

宿主机路径需要按实际安装位置填写，例如：

```yaml
- /your/host/path/trimmedia.db:/fntv/trimmedia.db:ro
```

`fntv-admin` 不会在代码中写宿主机路径，也不会写入飞牛影视数据库。

## 只读要求

必须满足：

- Docker Compose 挂载使用 `:ro`。
- 后端使用 SQLite `mode=ro` 打开。
- 后端连接启用 `PRAGMA query_only = ON`。
- 增强数据只写入 `/data/admin.db`。

