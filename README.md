# fntv-admin

`fntv-admin` 是从零开发的飞牛影视增强管理后台。项目官方只支持 Docker Compose 部署，生产环境优先使用一个容器运行 FastAPI 后端和 Vue 构建后的静态前端。

飞牛 NAS 默认推荐直接拉取 Docker Hub 成品镜像运行，不推荐在飞牛本机 build 镜像。GHCR 作为备用镜像源。

核心边界：

- Docker Compose 是唯一官方部署入口。
- 默认部署使用 Docker Hub 成品镜像。
- GHCR 仅作为备用镜像源。
- 飞牛影视数据库目录挂载到 `/fntv`，应用代码层只读打开 `/fntv/trimmedia.db`。
- 所有增强数据写入 `/data/admin.db`。
- 默认本地和外部访问都需要登录；可在系统设置中开启本地免登录，外部访问仍需登录或可禁止。
- 所有可变数据都保存在 `/data`。
- 不提供裸机、PM2、手动 Nginx、宝塔或 systemd 生产部署方式。

## 快速开始

1. 复制 `docker-compose.yml` 到飞牛 NAS 的应用目录。

2. 确认镜像地址。官方默认示例使用 `eliyork`：

```yaml
services:
  fntv-admin:
    # 默认源: Docker Hub.
    # 备用源: ghcr.io/eliyork/fntv-admin:latest
    image: docker.io/eliyork/fntv-admin:latest
    container_name: fntv-admin
    restart: unless-stopped

    ports:
      - "8080:8080"

    volumes:
      # 后台数据目录，需读写
      - ./data:/data

      # 飞牛影视数据库目录，不加 :ro；应用层仍只读访问
      - /usr/local/apps/@appdata/trim.media/database:/fntv

    environment:
      APP_ENV: production
      APP_SECRET_KEY: change-this-to-a-long-random-string

      FNTV_DB_PATH: /fntv/trimmedia.db
      ADMIN_DB_PATH: /data/admin.db
      LOG_DIR: /data/logs
      CACHE_DIR: /data/cache
      BACKUP_DIR: /data/backup
      DEFAULT_PAGE_SIZE: "20"
      LOG_RETENTION_DAYS: "14"
      TRUST_PROXY_HEADERS: "false"
      SNAPSHOT_ENABLED: "false"
      ACTIVE_WATCH_WINDOW_SECONDS: "300"
```

3. 检查挂载路径：

```text
飞牛影视数据库目录：/usr/local/apps/@appdata/trim.media/database -> /fntv
fntv-admin 数据目录：./data -> /data 读写
```

`FNTV_DB_PATH` 保持 `/fntv/trimmedia.db`。不要把飞牛影视数据库目录挂到 `/data`。

4. 启动：

```bash
docker compose up -d
```

5. 打开：

```text
http://localhost:8080
```

在飞牛 NAS 上访问时，把 `localhost` 换成飞牛 IP：

```text
http://飞牛IP:8080
```

首次进入时创建管理员账号。管理员密码只会以 hash 形式写入 `/data/admin.db`。

`APP_SECRET_KEY` 必须在部署前改成足够长的随机字符串，不要沿用示例值。

## 访问控制

登录系统不会被删除。默认策略是：

```text
本地访问：需要登录
外部访问：需要登录
TRUST_PROXY_HEADERS=false
```

系统设置页提供“访问控制”区域，可分别设置本地访问为“需要登录 / 免登录”，外部访问为“需要登录 / 禁止访问”。本地免登录仅适合可信飞牛内网使用；外部访问设置为“禁止访问”时，非本地来源会直接返回 403。

本地来源包括 `127.0.0.1`、`::1`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`fc00::/7`、`fe80::/10`。如果通过公网、DDNS 或反向代理访问，建议保持本地和外部都需要登录，或将外部访问设为禁止。

默认不信任 `X-Forwarded-For` / `X-Real-IP`。只有确认反向代理会正确覆盖这些请求头时，才谨慎设置 `TRUST_PROXY_HEADERS=true`，否则可能被伪造来源绕过本地/外部判断。

## 镜像地址

默认 Docker Hub 镜像：

```text
docker.io/eliyork/fntv-admin:latest
docker.io/eliyork/fntv-admin:v0.7.2
```

备用 GHCR 镜像：

```text
ghcr.io/eliyork/fntv-admin:latest
ghcr.io/eliyork/fntv-admin:v0.7.2
```

GitHub Actions 会在以下场景构建并推送镜像：

- push 到 `main` 分支。
- push `v*.*.*` 版本 tag。
- 手动触发 `workflow_dispatch`。

如果 fork 后要发布自己的镜像，可以把示例中的 `eliyork` 改成自己的账号；官方默认示例保持 `eliyork`。

GHCR 镜像名格式：

```text
ghcr.io/eliyork/fntv-admin:latest
ghcr.io/eliyork/fntv-admin:sha-<git-sha>
ghcr.io/eliyork/fntv-admin:<tag>
```

如果仓库默认分支不是 `main`，需要在 `.github/workflows/docker-image.yml` 中把触发分支改成实际默认分支。

## 数据持久化

容器内固定路径：

```text
/fntv/trimmedia.db    飞牛影视数据库，由 /fntv 目录挂载提供，应用代码层只读打开
/data/admin.db        fntv-admin 增强数据
/data/logs            运行日志
/data/cache           缓存
/data/backup          备份
```

只要 `/data` 保留，删除并重建容器不会丢失后台配置、备注、隐藏状态、认证策略和快照设置。

## 飞牛数据库只读保护

`docker-compose.yml` 默认包含：

```yaml
- /usr/local/apps/@appdata/trim.media/database:/fntv
```

飞牛影视实机可能使用 SQLite WAL 模式。Docker 层给 `/fntv` 加 `:ro` 时，SQLite 可能因为无法访问或维护 `-wal`、`-shm`、锁相关文件而报 `unable to open database file`。因此飞牛默认 Compose 不再给 `/fntv` 写 `:ro`。

`/data` 必须读写挂载，否则 `admin.db`、日志和缓存无法持久化。飞牛数据库的安全边界由应用代码层保证：后端通过 SQLite URI `mode=ro` 打开飞牛数据库，并在连接上设置 `PRAGMA query_only = ON`。业务代码不提供任何飞牛数据库写入接口，`python scripts/verify_fntv_readonly.py` 必须通过。

## 飞牛源库直读与可选快照

默认直接只读读取 `/fntv/trimmedia.db`。后端使用 SQLite URI `mode=ro` 打开源库，并设置 `PRAGMA query_only = ON`。即使飞牛 Docker UI 中显示数据库目录不是只读挂载，代码层仍会拒绝写入飞牛数据库。

Phase 7C 增加可选快照读取。默认 `SNAPSHOT_ENABLED=false`，系统仍走源库只读直连。开启后，后端会尝试用 SQLite backup API 生成 `/data/cache/trimmedia.snapshot.db`，业务查询优先读取快照；如果快照生成或打开失败，会自动回退源库只读直连，系统诊断页显示失败原因和 `fallback_to_source`。

快照只写入 `/data/cache`，不复制 `.wal/.shm` 作为主要方案，不写飞牛影视数据库，不改变 `/fntv` 挂载语义。

## 开发者本地构建

以下命令仅用于开发者本地测试，不是官方生产部署方式，也不是飞牛可视化部署默认路径：

```bash
docker compose -f docker-compose.build.yml build
docker compose -f docker-compose.build.yml up -d
```

## 飞牛可视化部署

飞牛 Docker 可视化界面部署步骤见 [docs/FNOS_GUI_DEPLOY.md](docs/FNOS_GUI_DEPLOY.md)。

## 当前阶段

当前实现已覆盖以下基础后台能力：

- Docker Compose-first 项目结构。
- FastAPI 后端与 Vue 前端。
- 单容器生产 Dockerfile。
- Docker Hub 为默认成品镜像源，GHCR 作为备用发布目标。
- 启动检查、健康检查、数据库状态。
- 首次管理员初始化、登录、退出、当前用户、修改密码。
- 仪表盘首页采用浅蓝玻璃拟态监控面板风格，展示总览指标、最近活跃观看、播放时段、观看历史、热门内容、收藏记录和下载记录简版。
- 观看历史、用户管理、媒体库基础 API 与页面。
- 观看历史支持分页、搜索、CSV 导出和播放进度条展示；飞牛 `item.runtime` 小整数按分钟归一化，避免 44 分钟被显示成 44 秒。
- 用户管理支持搜索、隐藏用户和后端表头排序。
- 媒体库优化剧集/季/单集标题展示，避免重复拼接；隐藏操作写入 `admin.db`。
- Phase 7B 报表中心基础统计：总览、播放趋势 GitHub-style 日期热力图、活跃用户榜、热门媒体榜单集/整部剧统计模式、媒体类型中文展示、分辨率“未记录”说明。
- 报表中心切换范围或刷新时保留上次成功数据，后台更新失败只显示模块内提示，不弹出误导性的登录错误。
- Phase 7C 增加播放时段分布、收藏记录只读列表、下载记录只读诊断、最近活跃观看推断、观看历史时间范围筛选和增强 CSV 导出。
- 最近活跃观看使用最近 5 分钟播放记录更新时间推断，不是真正实时 session。
- 系统诊断显示快照状态、新增表能力和 `watched` 字段取值诊断；诊断不返回真实播放记录行。
- 系统设置支持主题、本地访问认证策略和外部访问认证策略；系统诊断页提供飞牛数据库状态、schema 诊断、只读状态和右上角复制诊断信息。

飞牛数据库表结构不确定时，页面会显示空状态或数据库异常提示，不会导致应用崩溃。

报表中心通过后端 SQL 聚合只读统计当前 active 数据库；默认仍使用源库只读直连。可选快照仅作为增强读取模式，默认关闭，失败会自动回退源库。增强配置、账号和后续缓存类数据只允许写入 `/data/admin.db`。

## 特别感谢 / 参考项目

本项目从零开发，不 fork、不复制以下项目的代码、结构、资源或样式；开发过程中仅参考了公开项目在交互展示、数据口径和只读管理思路上的经验：

- fntv-record-view：飞牛影视观看记录展示、字段口径参考。
- [fnmedia-monitor](https://github.com/deepvoce/fnmedia-monitor)：飞牛影视监控面板、播放时段、下载/收藏/最近活跃观看等只读数据展示思路参考。
- fntv-electron：飞牛影视桌面端封装思路参考。
- fnos-tv：基于飞牛影视接口的网页端实现参考。

## License

License 待补充。

第三方项目、依赖和素材版权归原作者所有，以其原项目 License 为准。
