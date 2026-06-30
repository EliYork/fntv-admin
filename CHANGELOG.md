# Changelog

## 0.1.0 - Unreleased

- 建立 Docker Compose-first 项目基础。
- 增加 FastAPI 后端、Vue 前端和单容器 Dockerfile。
- 增加飞牛数据库只读连接、启动检查和 admin.db 初始化。
- 增加登录权限、仪表盘、观看历史、用户管理、媒体库基础能力。
- 增加 GitHub Actions 自动构建并推送 Docker Hub 与 GHCR 镜像。
- 默认 Docker Compose 部署改为拉取 Docker Hub 成品镜像 `docker.io/eliyork/fntv-admin:latest`，保留开发者本地构建 compose。
- GHCR 镜像 `ghcr.io/eliyork/fntv-admin:latest` 作为备用镜像源。
- V1 禁用飞牛数据库 snapshot 快照机制，业务接口统一通过 SQLite 只读源库直连读取 `/fntv/trimmedia.db`。
- 增加 Phase 7A 报表中心基础统计，包含总览、播放趋势、活跃用户榜、热门媒体榜、媒体类型分布和分辨率分布。
- 报表接口在后端 SQL 层聚合飞牛影视只读源库数据，不写入飞牛数据库，不恢复 snapshot。
- 调整飞牛默认 Compose 数据库挂载为 `/usr/local/apps/@appdata/trim.media/database:/fntv`，记录 WAL/SHM 场景下 Docker 层 `:ro` 可能导致 `unable to open database file`；应用代码层仍使用 SQLite `mode=ro` 和 `PRAGMA query_only = ON` 保证只读。
- 增加本地/外部访问认证策略设置：默认本地和外部都需要登录，可在系统设置中开启本地免登录，外部访问可保持登录保护或禁止访问；代理头默认不信任。
- 系统设置页聚焦主题和本地/外部访问认证策略；系统诊断页提供飞牛数据库状态、schema 诊断、只读状态和复制诊断信息。
- 修复已登录后页面切换时普通业务接口 401 误清 Token 并跳回登录页的问题，登录态失效前会先复核 `/api/auth/me`。
- Phase 7B 整理页面体验：仪表盘最近活动改为 20 条并取消内部滚动，观看历史增加进度条，用户管理支持后端表头排序，媒体库优化标题展示并隐藏未接入编辑的备注列。
- 报表中心播放趋势改为日期热力图，媒体类型中文展示，热门媒体支持单集/整部剧统计模式，分辨率空值统一显示为“未记录”。
- Phase 7B 收尾：播放趋势热力图改为周列/星期行布局并提供即时 tooltip；报表刷新采用 stale-while-revalidate，失败时保留上次成功数据。
- 修正观看历史媒体总时长归一化，`item.runtime` 小整数按分钟处理，并可优先使用批量读取的媒体流 duration。
- 观看历史标题搜索参考飞牛层级查询口径，增加父级和祖父级媒体标题匹配，搜索剧名时可命中单集播放记录。
- 优化前端错误提示：业务 401 复核 `/api/auth/me`，403 不再提示登录，500 不再误触发“请先登录”，重复错误提示会节流。
- 修复后台主布局滚动结构，左侧菜单与顶部栏保持稳定；暂不暴露任务中心和日志中心入口；系统诊断右上角增加复制诊断信息。
- Phase 7C 综合增强：增加可选 SQLite 快照读取、播放时段分布、最近活跃观看推断、收藏记录只读列表、下载记录只读诊断、观看历史时间范围筛选、增强 CSV 导出和 `watched` 字段诊断。
- 可选快照默认关闭，只写 `/data/cache/trimmedia.snapshot.db`；快照失败时自动回退源库只读直连，不改变 `/data` 与 `/fntv` 挂载语义。
- 仪表盘首页改为浅蓝玻璃拟态监控面板风格，集中展示最近活跃观看、播放时段、观看历史、热门内容、收藏记录和下载记录简版。
- 修复亮暗主题切换后 `html.dark` / `body.dark` 可能残留的问题，统一主题状态、`data-theme` 和 Element Plus dark class。
