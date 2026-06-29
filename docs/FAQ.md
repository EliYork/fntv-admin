# FAQ

## 是否支持裸机部署？

不作为官方生产部署方式支持。官方只支持 Docker Compose。

## 飞牛数据库不存在时会怎样？

应用会继续启动，`/api/system/database-status` 和前端顶部状态会提示数据库异常。容器不会因为飞牛数据库缺失而无限重启。

## 会修改飞牛影视数据库吗？

不会。飞牛默认部署不再依赖 Docker 层 `:ro`，后端会使用 SQLite URI `mode=ro` 打开 `/fntv/trimmedia.db`，并设置 `PRAGMA query_only = ON`。V1 不生成 snapshot 快照，不 checkpoint 源库，不删除或修改源库 wal/shm 文件。备注、隐藏状态、管理员账号、任务日志等增强数据只写入 `/data/admin.db`。`python scripts/verify_fntv_readonly.py` 必须通过。

## 公网访问安全吗？

项目默认面向内网 NAS。公网访问必须使用 HTTPS 反向代理、强密码、登录失败限制，并且不要直接暴露未加保护的管理后台。

## 可以在内网免登录吗？

可以。系统设置页的“访问控制”可以设置为：

```text
本地访问：免登录
外部访问：需要登录
```

这适合可信飞牛内网自用。默认仍是本地和外部都需要登录。外部访问不能设置为免登录，只能选择需要登录或禁止访问。

## 外部访问禁止是什么意思？

当“外部访问”设置为“禁止访问”时，不属于本地网段的请求会直接返回 403。公网、DDNS 或反向代理场景建议保持外部访问需要登录，或直接禁止外部访问。

默认不信任 `X-Forwarded-For` / `X-Real-IP`。只有确认反向代理会覆盖并清理这些请求头时，才设置 `TRUST_PROXY_HEADERS=true`，否则可能被伪造来源影响本地/外部判断。

## 系统设置显示"只读连接：是，但结构读取失败"怎么办？

这说明飞牛数据库挂载大概率是成功的，后端可以只读打开数据库。问题出在飞牛数据库的表结构与 fntv-admin 适配器不完全匹配。

排查步骤：

1. 进入系统设置页，查看"飞牛数据库诊断"区域。
2. 确认"检测到的表数量"是否大于 0。
3. 查看"核心表匹配状态"，确认用户表、媒体表、播放记录表是否已匹配。
4. 点击"复制诊断信息"按钮，将脱敏 JSON 发给开发者。

不要做的事：

1. 不要反复修改 Docker Compose 挂载路径。
2. 不要删除 `/data` 目录。
3. 不要绕过应用代码层只读保护。

该问题通常是飞牛版本数据库字段差异导致的，需要在 fntv-admin 中做适配。提供诊断信息可以帮助开发者快速定位缺失的表或字段。

## 飞牛数据库报 "unable to open database file" 怎么办？

V1 使用源库只读直连读取 `/fntv/trimmedia.db`。飞牛影视实机可能使用 SQLite WAL 模式；如果 Docker 层给 `/fntv` 追加 `:ro`，SQLite 可能因为无法访问或维护 `-wal`、`-shm`、锁相关文件而报 `unable to open database file`。

检查：

1. `/usr/local/apps/@appdata/trim.media/database` 是否挂载到 `/fntv`。
2. 容器内 `/fntv/trimmedia.db` 是否存在。
3. Compose 中是否使用默认挂载 `/usr/local/apps/@appdata/trim.media/database:/fntv`，不要在飞牛实机下强制追加 `:ro`。
4. 系统设置页点击"复制诊断信息"，查看 `availability` 和错误描述。

去掉 Docker 层 `:ro` 不代表应用会写飞牛数据库。应用仍使用 SQLite `mode=ro` 和 `PRAGMA query_only = ON`，并应通过 `python scripts/verify_fntv_readonly.py` 验证。

不要做的事：

1. 不要反复修改挂载路径。
2. 不要把飞牛数据库目录挂到 `/data`。
3. 不要删除 `/data` 目录。
