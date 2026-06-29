# fntv-admin 设计文档

## 1. 项目名称

项目名称：`fntv-admin`

中文名称：飞牛影视增强管理后台

项目定位：

`fntv-admin` 是一个独立开发的飞牛影视增强管理后台，用于在不修改飞牛影视原始数据库的前提下，读取飞牛影视的用户、媒体、播放历史等数据，并提供类似 Emby 后台管理体验的可视化管理、统计分析、系统维护、日志查看、任务管理和个性化配置能力。

本项目不 fork 任何已有项目，不继承其他项目的代码结构。已有同类项目只作为需求参考，不作为代码基础。

---

## 2. 核心目标

### 2.1 产品目标

1. 提供一个完整、正式、长期可维护的飞牛影视后台管理系统。
2. 支持 Docker Compose 一键部署，适配 NAS、飞牛、Linux 家庭服务器。
3. 只读读取飞牛影视数据库，不写入、不删除、不修改飞牛原始数据。
4. 所有增强配置写入项目自己的 `admin.db`。
5. 当前提供仪表盘、观看历史、用户管理、媒体库、报表中心、系统设置、系统诊断等模块；任务中心和日志中心作为后续维护能力规划，不在当前 UI 中暴露入口。
6. 从第一版开始使用正式架构，而不是临时代码堆叠。
7. 开发结构前后端分离，生产部署单容器优先。
8. 后续可扩展为家庭媒体数据中心。

---

## 3. 非目标

V1 不做以下内容：

1. 不替代飞牛影视本体。
2. 不实现媒体播放功能。
3. 不实现转码功能。
4. 不实现媒体下载、刮削、自动整理。
5. 不修改飞牛影视原用户、媒体、播放记录。
6. 不支持裸机部署。
7. 不提供 Python/Node 本地安装教程。
8. 不提供 Nginx 手动部署教程。
9. 不做公网 SaaS。
10. 不追求第一版覆盖 Emby 后台的全部能力。

---

## 4. 部署原则

### 4.1 Docker Compose-only

本项目官方只支持 Docker Compose 部署。

官方文档只提供：

```text
docker compose up -d
```

不提供：

```text
裸机 Python 部署
裸机 Node 部署
手动 Nginx 部署
宝塔手动部署
PM2 部署
```

项目可以在开发环境本地启动前后端，但这不是官方生产部署方式。

飞牛 NAS 默认推荐拉取 Docker Hub 成品镜像运行，不要求在飞牛本机 build 镜像；GHCR 作为备用镜像源。

---

### 4.2 单容器生产部署

生产环境优先使用单容器：

```text
fntv-admin 容器
├── FastAPI 后端
├── Vue 构建后的静态文件
├── API 服务
├── 前端静态资源服务
└── 后台任务与日志
```

用户只需要：

1. 配置 Docker Hub 镜像地址
2. 挂载项目数据目录 `/data`
3. 挂载飞牛影视数据库目录到 `/fntv`
4. 启动 Docker Compose

---

### 4.3 容器内固定路径

容器内路径固定：

```text
/fntv/trimmedia.db    飞牛影视数据库，应用代码层只读
/data/admin.db        fntv-admin 自己的管理数据库
/data/logs            日志目录
/data/cache           缓存目录
/data/backup          备份目录
```

用户只需要在 `docker-compose.yml` 中修改宿主机挂载路径。

---

## 5. 核心边界

### 5.1 飞牛数据库只读

飞牛影视数据库只作为数据源。

禁止对飞牛数据库执行：

```sql
INSERT
UPDATE
DELETE
DROP
ALTER
VACUUM
REINDEX
```

后端必须使用 SQLite 只读连接。

Docker Compose 默认挂载飞牛影视数据库目录，不在 FNOS 实机下追加 Docker 层 `:ro`：

```yaml
- /usr/local/apps/@appdata/trim.media/database:/fntv
```

飞牛影视实机可能使用 SQLite WAL 模式。Docker 层强制只读可能阻止 SQLite 访问或维护 `-wal`、`-shm`、锁相关文件，导致 `unable to open database file`。只读保护由 SQLite `mode=ro`、`PRAGMA query_only = ON` 和 `scripts/verify_fntv_readonly.py` 保证。

---

### 5.2 增强数据独立存储

所有后台增强数据存入自己的 `admin.db`。

包括：

```text
后台管理员账号
系统设置
主题设置
用户备注
用户别名
隐藏用户
媒体备注
隐藏媒体
收藏媒体
仪表盘配置
任务日志
操作审计
报表缓存
API Token
```

---

### 5.3 原始数据与增强数据分离

示例：

飞牛原始用户：

```text
guid = abc123
username = zhangsan
```

fntv-admin 增强信息：

```text
display_name = 老爸的账号
note = 客厅电视使用
hidden = false
```

增强信息只存入 `admin.db`，不修改飞牛原库。

---

## 6. 推荐技术栈

### 6.1 后端

```text
Python 3.12+
FastAPI
Uvicorn
SQLAlchemy
Pydantic
SQLite
APScheduler 或轻量任务队列
```

后端职责：

1. 读取飞牛数据库。
2. 管理 `admin.db`。
3. 提供 API。
4. 托管前端静态文件。
5. 执行后台任务。
6. 记录日志。
7. 管理登录和权限。

---

### 6.2 前端

```text
Vue 3
Vite
TypeScript
Pinia
Vue Router
Element Plus 或 Naive UI
ECharts
Axios
```

前端职责：

1. 后台管理界面。
2. 登录界面。
3. 仪表盘。
4. 表格筛选。
5. 图表展示。
6. 系统设置。
7. 任务和日志查看。

---

### 6.3 部署

```text
Docker
Docker Compose
```

生产镜像使用多阶段构建：

1. Node 阶段构建前端。
2. Python 阶段安装后端依赖。
3. 将前端 `dist` 复制到后端镜像。
4. FastAPI 同时提供 API 和前端静态页面。
5. 最终只运行一个容器。

---

## 7. 总体架构

```text
用户浏览器
   │
   ▼
fntv-admin 单容器
   │
   ├── Vue 静态前端
   ├── FastAPI 后端 API
   ├── 只读读取 /fntv/trimmedia.db
   ├── 读写 /data/admin.db
   ├── 写入 /data/logs
   └── 写入 /data/cache
```

---

## 8. 数据流

### 8.1 原始数据读取

```text
飞牛影视数据库 trimmedia.db
   ↓ SQLite mode=ro + PRAGMA query_only
FastAPI service 层
   ↓
API response
   ↓
Vue 前端展示
```

### 8.2 增强数据写入

```text
Vue 前端操作
   ↓
FastAPI API
   ↓
admin.db
```

### 8.3 报表缓存

```text
飞牛数据库 + admin.db
   ↓
报表计算任务
   ↓
cache_entries
   ↓
报表 API
```

Phase 7A/7B 先不启用报表缓存和任务化预计算。当前报表中心直接通过 SQLite 只读连接对飞牛源库做 SQL 聚合，返回基础统计结果；Phase 7B 将播放趋势整理为热力图，并增加热门媒体单集/整部剧统计模式。前端刷新使用 stale-while-revalidate 展示策略，只保留浏览器内上次成功结果，不把报表缓存写入 `admin.db` 或 `/data/cache`。后续进入任务中心与缓存阶段时，再把可缓存报表写入 `admin.db` 或 `/data/cache`。

---

## 9. 项目目录结构

```text
fntv-admin/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   ├── errors.py
│   │   │   └── response.py
│   │   ├── db/
│   │   │   ├── fntv_readonly.py
│   │   │   ├── admin_db.py
│   │   │   ├── migrations.py
│   │   │   └── schema_check.py
│   │   ├── models/
│   │   │   ├── admin_user.py
│   │   │   ├── setting.py
│   │   │   ├── user_profile.py
│   │   │   ├── media_profile.py
│   │   │   ├── task_log.py
│   │   │   ├── audit_log.py
│   │   │   └── cache_entry.py
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── dashboard.py
│   │   │   ├── history.py
│   │   │   ├── user.py
│   │   │   ├── media.py
│   │   │   ├── report.py
│   │   │   ├── task.py
│   │   │   ├── log.py
│   │   │   ├── setting.py
│   │   │   └── common.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── dashboard_service.py
│   │   │   ├── history_service.py
│   │   │   ├── user_service.py
│   │   │   ├── media_service.py
│   │   │   ├── report_service.py
│   │   │   ├── task_service.py
│   │   │   ├── log_service.py
│   │   │   └── system_service.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── dashboard.py
│   │   │   ├── history.py
│   │   │   ├── users.py
│   │   │   ├── media.py
│   │   │   ├── reports.py
│   │   │   ├── tasks.py
│   │   │   ├── logs.py
│   │   │   ├── settings.py
│   │   │   └── system.py
│   │   ├── static/
│   │   │   └── frontend build output
│   │   └── utils/
│   │       ├── time.py
│   │       ├── pagination.py
│   │       └── sqlite.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/
│   │   ├── stores/
│   │   ├── api/
│   │   ├── layouts/
│   │   ├── views/
│   │   ├── components/
│   │   ├── styles/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
├── docs/
│   ├── DESIGN.md
│   ├── DOCKER_COMPOSE.md
│   ├── FNTV_DATABASE_PATH.md
│   ├── BACKUP.md
│   ├── UPGRADE.md
│   └── FAQ.md
├── scripts/
│   └── inspect_fntv_db.py
├── data/
│   ├── .gitkeep
│   ├── logs/
│   ├── cache/
│   └── backup/
├── docker-compose.yml
├── .env.example
├── README.md
├── AGENTS.md
└── CHANGELOG.md
```

---

## 10. Docker Compose 设计

### 10.1 官方 docker-compose.yml

```yaml
services:
  fntv-admin:
    image: docker.io/eliyork/fntv-admin:latest
    container_name: fntv-admin
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /vol1/Docker/fntv-admin/data:/data
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
```

备用 GHCR 镜像为 `ghcr.io/eliyork/fntv-admin:latest`。

开发者本地构建使用 `docker-compose.build.yml`，不是飞牛部署默认路径。

---

### 10.2 .env.example

```env
APP_NAME=fntv-admin
APP_ENV=production
APP_SECRET_KEY=change-me

FNTV_DB_PATH=/fntv/trimmedia.db
ADMIN_DB_PATH=/data/admin.db
LOG_DIR=/data/logs
CACHE_DIR=/data/cache
BACKUP_DIR=/data/backup

DEFAULT_PAGE_SIZE=20
LOG_RETENTION_DAYS=14
```

---

## 11. Dockerfile 设计

生产镜像使用多阶段构建。

```dockerfile
# frontend build
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build


# backend runtime
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend-builder /frontend/dist ./app/static

RUN mkdir -p /data/logs /data/cache /data/backup /fntv

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 12. 启动检查

容器启动时后端必须检查：

1. `/data` 是否存在。
2. `/data` 是否可写。
3. `/data/logs` 是否存在，不存在则创建。
4. `/data/cache` 是否存在，不存在则创建。
5. `/data/backup` 是否存在，不存在则创建。
6. `/fntv/trimmedia.db` 是否存在。
7. 飞牛数据库是否可以只读打开。
8. 飞牛数据库是否包含必要表。
9. `admin.db` 是否存在，不存在则初始化。
10. `admin.db` 是否需要迁移。

如果飞牛数据库不存在，后台仍应启动，但系统状态显示为异常，并提示用户检查挂载路径。

---

## 13. 后端 API 设计

### 13.1 通用响应格式

成功：

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

失败：

```json
{
  "success": false,
  "error": {
    "code": "DATABASE_NOT_FOUND",
    "message": "飞牛影视数据库不存在，请检查 Docker Compose 挂载路径"
  }
}
```

分页：

```json
{
  "success": true,
  "data": {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 100,
    "pages": 5
  }
}
```

---

### 13.2 Auth API

```text
POST /api/auth/init-admin
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
POST /api/auth/change-password
```

---

### 13.3 System API

```text
GET /api/system/health
GET /api/system/database-status
GET /api/system/storage-status
GET /api/system/version
```

---

### 13.4 Dashboard API

```text
GET /api/dashboard/overview
GET /api/dashboard/recent-activities
GET /api/dashboard/play-trend
GET /api/dashboard/top-media
GET /api/dashboard/top-users
GET /api/dashboard/system-status
```

---

### 13.5 History API

```text
GET /api/history
GET /api/history/:id
GET /api/history/export
```

筛选参数：

```text
user_guid
keyword
media_type
watched
resolution
progress_min
progress_max
start_time
end_time
page
page_size
sort_by
sort_order
```

---

### 13.6 Users API

```text
GET    /api/users
GET    /api/users/:guid
GET    /api/users/:guid/history
GET    /api/users/:guid/stats
PUT    /api/users/:guid/profile
POST   /api/users/:guid/hide
POST   /api/users/:guid/unhide
```

---

### 13.7 Media API

```text
GET  /api/media
GET  /api/media/tree
GET  /api/media/:guid
GET  /api/media/:guid/children
GET  /api/media/:guid/history
GET  /api/media/:guid/stats
PUT  /api/media/:guid/profile
POST /api/media/:guid/hide
POST /api/media/:guid/unhide
```

---

### 13.8 Reports API

```text
GET /api/reports/overview
GET /api/reports/play-trend?days=30
GET /api/reports/top-users?days=30&limit=10
GET /api/reports/top-media?days=30&limit=10
GET /api/reports/media-type-distribution
GET /api/reports/resolution-distribution?days=30
```

Phase 7A/7B 的报表 API 均需要登录鉴权，只读读取飞牛源库，不写飞牛数据库。播放趋势、活跃用户、热门媒体和分辨率分布在后端 SQL 层按时间范围聚合；播放趋势支持 7、30、90 和最多 365 天的 `all` 热力图，榜单和分辨率分布支持 `all`，热门媒体支持 `episode` / `series` 统计模式，服务层会限制最大天数和最大 `limit`。更复杂的完播率排行、弃剧排行、观看时段热力图和缓存预计算留到后续阶段。

---

### 13.9 Tasks API

```text
GET  /api/tasks
GET  /api/tasks/:id
POST /api/tasks/refresh-database
POST /api/tasks/rebuild-cache
POST /api/tasks/health-check
POST /api/tasks/cleanup-logs
```

---

### 13.10 Logs API

```text
GET    /api/logs
GET    /api/logs/download
DELETE /api/logs/cleanup
```

---

### 13.11 Settings API

```text
GET /api/settings
PUT /api/settings
GET /api/settings/database
PUT /api/settings/database
GET /api/settings/theme
PUT /api/settings/theme
GET /api/settings/auth-policy
PUT /api/settings/auth-policy
```

---

## 14. 页面设计

### 14.1 登录页

路径：

```text
/login
```

功能：

1. 管理员登录。
2. 首次启动创建管理员账号。
3. 登录失败提示。
4. 登录状态保持。
5. 退出登录。

---

### 14.2 后台主布局

路径：

```text
/
```

布局：

```text
左侧导航栏
顶部状态栏
主内容区
右侧详情抽屉
```

左侧导航当前暴露：

```text
仪表盘
观看历史
用户管理
媒体库
报表中心
系统设置
系统诊断
```

顶部状态栏：

```text
数据库状态
最后刷新时间
当前登录用户
主题切换
退出登录
```

---

### 14.3 仪表盘

路径：

```text
/dashboard
```

模块：

1. 总用户数。
2. 总媒体数。
3. 总播放记录。
4. 今日播放次数。
5. 最近播放活动。
6. 近 7 日播放趋势。
7. 热门媒体排行。
8. 用户活跃排行。
9. 系统状态卡片。

---

### 14.4 观看历史

路径：

```text
/history
```

功能：

1. 播放历史表格。
2. 用户筛选。
3. 标题搜索。
4. 时间范围筛选。
5. 是否看完筛选。
6. 分辨率筛选。
7. 分页。
8. 排序。
9. 播放进度条展示，缺失总时长时只显示当前位置，异常进度最多显示 100%。
10. 媒体总时长优先使用可批量读取的媒体流 duration；仅有 `item.runtime` 时，1 到 600 的整数按分钟归一化，较大秒数和毫秒值按秒处理。
11. 详情抽屉。
12. CSV 导出。

---

### 14.5 用户管理

路径：

```text
/users
```

功能：

1. 用户列表。
2. 用户搜索。
3. 是否管理员展示。
4. 最近登录时间。
5. 最近播放时间。
6. 播放次数。
7. 总观看时长。
8. 用户备注。
9. 用户别名。
10. 隐藏用户。
11. 表头后端排序：用户名、播放次数、观看时长、最近播放、最近登录。

用户详情页：

```text
/users/:guid
```

---

### 14.6 媒体库

路径：

```text
/media
```

功能：

1. 媒体列表。
2. 媒体搜索。
3. 媒体类型筛选。
4. 剧集层级。
5. 媒体详情。
6. 子项目列表。
7. 播放统计。
8. 谁看过这个媒体。
9. 媒体备注。
10. 隐藏媒体。
11. 标题展示避免剧名、季号、集号和文件名重复拼接；列表页暂不展示未接入编辑入口的管理备注列。

媒体详情页：

```text
/media/:guid
```

---

### 14.7 报表中心

路径：

```text
/reports
```

报表：

Phase 7B 基础可用版：

1. 报表总览。
2. 播放趋势日期热力图，按周为列、星期为行展示，支持 7 / 30 / 90 / all 范围，all 最多 365 天。
3. 活跃用户榜。
4. 热门媒体榜，支持单集/整部剧统计模式。
5. 媒体类型分布，中文展示。
6. 分辨率分布，缺失值显示为“未记录”。
7. 报表模块使用 stale-while-revalidate：刷新和切换范围时保留上次成功数据，显示“正在更新”和最后更新时间；更新失败时只在模块内提示。

后续版本再扩展：

1. 每周、每月趋势。
2. 完播率排行。
3. 弃剧排行。
4. 观看时段热力图。
5. 报表缓存与后台任务预计算。

---

### 14.8 任务中心（后续规划，不在当前 UI 暴露）

路径：

```text
/tasks
```

功能：

1. 查看任务列表。
2. 手动检查数据库状态。
3. 手动重建报表缓存。
4. 健康检查。
5. 清理旧日志。
6. 查看任务状态。
7. 查看任务错误。

---

### 14.9 日志中心（后续规划，不在当前 UI 暴露）

路径：

```text
/logs
```

功能：

1. 查看运行日志。
2. 查看错误日志。
3. 查看任务日志。
4. 查看登录日志。
5. 按等级筛选。
6. 按时间筛选。
7. 下载日志。
8. 清理旧日志。

---

### 14.10 系统设置

路径：

```text
/settings
```

功能：

1. 主题设置。
2. 本地访问认证策略：需要登录 / 免登录。
3. 外部访问认证策略：需要登录 / 禁止访问。

数据库状态、schema 诊断、只读状态和复制诊断信息属于系统诊断页。

---

### 14.11 系统诊断

路径：

```text
/diagnostics
```

功能：

1. 飞牛数据库状态。
2. schema 诊断。
3. 只读状态。
4. 右上角复制诊断信息；自动复制失败时提供文本框手动复制。

---

## 15. admin.db 数据库设计

### 15.1 admin_users

```sql
CREATE TABLE admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    last_login_at INTEGER
);
```

---

### 15.2 settings

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'string',
    updated_at INTEGER NOT NULL
);
```

---

### 15.3 user_profiles

```sql
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fntv_user_guid TEXT NOT NULL UNIQUE,
    display_name TEXT,
    note TEXT,
    hidden INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
```

---

### 15.4 media_profiles

```sql
CREATE TABLE media_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fntv_item_guid TEXT NOT NULL UNIQUE,
    display_title TEXT,
    note TEXT,
    hidden INTEGER NOT NULL DEFAULT 0,
    favorite INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
```

---

### 15.5 task_logs

```sql
CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    started_at INTEGER NOT NULL,
    finished_at INTEGER,
    duration_ms INTEGER,
    error TEXT
);
```

---

### 15.6 audit_logs

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_user_id INTEGER,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    detail TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at INTEGER NOT NULL
);
```

---

### 15.7 cache_entries

```sql
CREATE TABLE cache_entries (
    cache_key TEXT PRIMARY KEY,
    cache_value TEXT NOT NULL,
    expired_at INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
```

---

## 16. 权限设计

### 16.1 V1 权限

V1 只提供一个角色：

```text
admin
```

admin 拥有：

```text
查看所有页面
修改系统设置
编辑备注
隐藏用户
隐藏媒体
执行任务
查看日志
导出数据
修改管理员密码
```

---

### 16.2 V2 权限

V2 可增加：

```text
admin
operator
viewer
```

说明：

```text
admin：全部权限
operator：查看数据、执行任务、编辑备注
viewer：只读查看
```

---

## 17. 安全设计

### 17.1 数据库安全

1. 飞牛数据库必须只读连接。
2. Docker Compose 默认将飞牛数据库目录挂载到 `/fntv`，FNOS / SQLite WAL / SHM 场景下不强制 `:ro`。
3. 任何写飞牛数据库的代码都不允许出现。
4. V1 直接只读读取 `/fntv/trimmedia.db`，不生成 snapshot 快照。
5. 应用层强制 SQLite `mode=ro` 和 `PRAGMA query_only = ON`。
6. `python scripts/verify_fntv_readonly.py` 必须验证没有飞牛数据库写入路径。
7. 查询失败时返回清晰错误。
8. 数据库路径不在前端暴露完整宿主机路径。

---

### 17.2 登录安全

1. 密码 hash 存储。
2. 禁止明文密码。
3. 登录失败限制频率。
4. Session/JWT 过期。
5. 默认建议内网访问。
6. 如果公网访问，必须 HTTPS 反代。

---

### 17.3 API 安全

1. 除登录和健康检查外，所有 API 需要认证。
2. 设置 API 需要管理员权限。
3. 任务 API 需要管理员权限。
4. 导出 API 需要认证。
5. 错误信息不能泄露敏感路径和堆栈。
6. 默认本地和外部访问都需要登录。
7. 系统设置可开启本地访问免登录，但外部访问只能保持登录保护或设置为禁止访问。
8. 默认不信任 `X-Forwarded-For` / `X-Real-IP`，只有 `TRUST_PROXY_HEADERS=true` 时才按代理头判断来源。
9. 公网、DDNS 或反向代理访问不建议关闭登录保护。

---

### 17.4 前端安全

1. 用户输入必须转义。
2. 禁止直接拼接未转义 HTML。
3. Token 不放 URL。
4. 退出登录后清理前端状态。
5. 表格和详情中的备注内容必须安全渲染。
6. 业务接口 401 需要先复核 `/api/auth/me`；复核成功时不清 Token、不跳登录、不弹“请先登录”，由当前模块展示局部错误。
7. 只有 `/api/auth/me` 也返回 401 时才清 Token 并跳转登录；403 显示无权限或禁止访问，500 不得被误判为登录失效。

---

## 18. 主题设计

V1 提供：

```text
浅色主题
深色主题
跟随系统
```

后续可增加：

```text
浅粉主题
蓝色主题
自定义强调色
```

默认主题应清爽、轻量，不使用过深或过重的视觉风格。

---

## 19. 分阶段开发计划

## Phase 0：项目准备与数据库探测

目标：

确认项目边界、Docker Compose 部署模型、飞牛数据库结构。

任务：

1. 创建新仓库 `fntv-admin`。
2. 创建基础目录。
3. 编写 `README.md`。
4. 编写 `docs/DESIGN.md`。
5. 编写 `AGENTS.md`。
6. 编写 `.env.example`。
7. 编写 `docker-compose.yml` 初稿。
8. 编写 `scripts/inspect_fntv_db.py`。
9. 探测飞牛数据库表结构。
10. 生成 `docs/FNTV_DB_SCHEMA.md`。

验收标准：

1. 项目目录清晰。
2. 可以只读打开飞牛数据库。
3. 可以列出核心表。
4. 不写入飞牛数据库。
5. Docker Compose 部署路径已经确定。

---

## Phase 1：Docker-first 正式项目骨架

目标：

完成前后端分离开发结构和单容器生产部署骨架。

后端任务：

1. 初始化 FastAPI。
2. 建立配置系统。
3. 建立日志系统。
4. 建立统一响应。
5. 建立统一错误处理。
6. 建立飞牛数据库只读连接模块。
7. 建立 `admin.db` 初始化模块。
8. 建立启动检查。
9. 提供 `/api/system/health`。
10. 提供 `/api/system/database-status`。

前端任务：

1. 初始化 Vue 3 + Vite + TypeScript。
2. 引入 UI 库。
3. 建立路由。
4. 建立后台布局。
5. 建立登录页占位。
6. 建立页面占位。
7. 建立 API 请求封装。
8. 建立主题切换基础。

Docker 任务：

1. 编写多阶段 Dockerfile。
2. 前端构建后复制到后端镜像。
3. FastAPI 托管前端静态文件。
4. Docker Compose 可启动。
5. `/data` 可持久化。
6. `/fntv/trimmedia.db` 只读挂载。

验收标准：

1. `docker compose up -d` 可启动。
2. 访问 `http://宿主机:8080` 能打开前端。
3. 前端能调用后端健康检查。
4. 数据库状态能正确显示。
5. `admin.db` 自动初始化。
6. 飞牛数据库不存在时系统不崩溃，而是显示错误状态。

---

## Phase 2：登录与权限

目标：

让系统成为真正后台，而不是裸页面。

任务：

1. 首次启动创建管理员。
2. 管理员登录。
3. 管理员退出。
4. 获取当前登录用户。
5. 修改密码。
6. 前端路由守卫。
7. 后端 API 鉴权。
8. 登录日志。
9. 操作审计基础。

验收标准：

1. 未登录不能访问后台。
2. 未登录不能访问业务 API。
3. 登录后可以进入后台。
4. 退出后无法继续访问。
5. 密码不明文存储。

---

## Phase 3：仪表盘 V1

目标：

完成可用的后台首页。

功能：

1. 总用户数。
2. 总媒体数。
3. 总播放记录数。
4. 今日播放次数。
5. 最近播放活动。
6. 近 7 日播放趋势。
7. 热门媒体排行。
8. 用户活跃排行。
9. 系统状态卡片。

验收标准：

1. 显示真实数据。
2. 数据为空时有空状态。
3. 数据库异常时有提示。
4. 图表加载不卡顿。

---

## Phase 4：观看历史 V1

目标：

完成完整观看历史管理页面。

功能：

1. 播放历史表格。
2. 用户筛选。
3. 标题搜索。
4. 时间范围筛选。
5. 是否看完筛选。
6. 分辨率筛选。
7. 分页。
8. 排序。
9. 详情抽屉。
10. CSV 导出。

验收标准：

1. 可以查看历史。
2. 可以筛选历史。
3. 可以搜索标题。
4. 可以查看详情。
5. 可以导出 CSV。
6. 大量数据分页稳定。

---

## Phase 5：用户管理 V1

目标：

完成用户列表和用户详情。

功能：

1. 用户列表。
2. 用户搜索。
3. 最近登录时间。
4. 最近播放时间。
5. 播放次数。
6. 总观看时长。
7. 用户详情。
8. 用户播放趋势。
9. 用户最近观看。
10. 用户备注。
11. 用户别名。
12. 隐藏用户。

验收标准：

1. 用户列表真实可用。
2. 用户详情真实可用。
3. 备注保存到 `admin.db`。
4. 隐藏用户不影响飞牛数据库。
5. 隐藏后可以恢复。

---

## Phase 6：媒体库 V1

目标：

完成媒体库浏览和媒体详情。

功能：

1. 媒体列表。
2. 媒体搜索。
3. 媒体类型筛选。
4. 剧集层级。
5. 媒体详情。
6. 子项目列表。
7. 播放统计。
8. 谁看过这个媒体。
9. 媒体备注。
10. 隐藏媒体。

验收标准：

1. 可以浏览媒体。
2. 可以搜索媒体。
3. 可以查看剧集层级。
4. 可以查看媒体详情。
5. 媒体备注保存到 `admin.db`。
6. 隐藏媒体不影响飞牛数据库。

---

## Phase 7：报表中心 V1

目标：

完成核心统计分析能力。

Phase 7A 先完成基础可用版，不进入任务中心、通知系统、多角色权限或自动调度。Phase 7B 只整理现有页面体验，不改变部署、认证边界和飞牛数据库只读读取方式。

功能：

1. 报表总览。
2. 播放趋势热力图，按周列、周一/周三/周五标签、中文月份和即时 tooltip 展示。
3. 活跃用户榜。
4. 热门媒体榜，支持单集/整部剧统计模式。
5. 媒体类型分布中文展示。
6. 分辨率分布，空值显示为“未记录”。
7. 模块刷新采用 stale-while-revalidate，失败时保留上次成功结果。

验收标准：

1. 报表数据真实。
2. 图表展示清晰。
3. 支持时间范围筛选。
4. 查询较慢时有加载状态。
5. 后端 SQL 聚合，不把全量媒体或播放记录交给前端统计。
6. 飞牛数据库只读读取，不写入、不生成 snapshot。
7. 刷新失败不清空已有报表数据，前端只显示局部错误。

---

## Phase 8：任务中心与缓存（后续规划）

目标：

让系统具备维护能力。

功能：

1. 手动检查数据库状态。
2. 手动重建仪表盘缓存。
3. 手动重建报表缓存。
4. 健康检查。
5. 清理旧日志。
6. 查看任务状态。
7. 查看任务错误。

验收标准：

1. 可以手动执行任务。
2. 任务状态清晰。
3. 失败有错误信息。
4. 任务日志写入 `admin.db`。
5. 同类任务不会危险并发。

---

## Phase 9：日志中心与系统设置（后续规划）

目标：

完成后台自管理能力。

日志中心：

1. 查看运行日志。
2. 查看错误日志。
3. 查看任务日志。
4. 查看登录日志。
5. 按等级筛选。
6. 按时间筛选。
7. 下载日志。
8. 清理旧日志。

系统设置：

1. 主题设置。
2. 本地访问认证策略。
3. 外部访问认证策略。

系统诊断：

1. 飞牛数据库状态。
2. schema 诊断。
3. 只读状态。
4. 右上角复制诊断信息。

验收标准：

1. 设置保存到 `admin.db`。
2. 修改后生效。
3. 日志可查看。
4. 日志可清理。
5. 敏感信息不泄露。

---

## Phase 10：文档、备份与 V1 发布

目标：

完成正式可用版本。

任务：

1. 完善 README。
2. 完善 Docker Compose 文档。
3. 编写飞牛数据库路径说明。
4. 编写备份文档。
5. 编写升级文档。
6. 编写 FAQ。
7. 增加版本号。
8. 增加 CHANGELOG。
9. 打 tag 发布。

验收标准：

1. 用户可按文档完成部署。
2. Docker Compose 一键启动。
3. 数据持久化正常。
4. 重启后配置不丢。
5. V1 功能完整可用。

---

## 20. V1 完成标准

V1 完成时必须具备：

```text
Docker Compose 部署
单容器生产镜像
管理员登录
后台布局
仪表盘
观看历史
用户管理
媒体库
报表中心
系统设置
系统诊断
飞牛数据库只读读取
admin.db 增强配置
完整文档
```

V1 不要求：

```text
裸机部署
多角色权限
多飞牛实例
自动通知
媒体播放
转码
公网企业级安全
移动 App
```

---

## 21. V2 规划

V2 目标：增强体验和分析能力。

功能：

1. 多角色权限。
2. 操作审计完善。
3. 媒体收藏。
4. 媒体标签。
5. 用户画像。
6. 家庭成员观看偏好。
7. 弃剧分析。
8. 追剧进度分析。
9. 媒体缺失检测。
10. 首页卡片自定义。
11. 报表导出。
12. API Token。
13. Webhook 通知。
14. Telegram / 企业微信通知。
15. 自动备份 `admin.db`。

---

## 22. V3 规划

V3 目标：成为家庭媒体数据中心。

功能：

1. 多飞牛实例支持。
2. 多数据源支持。
3. 跨实例用户统计。
4. 跨实例媒体统计。
5. 海报墙。
6. 家庭观影日历。
7. 年度观影报告。
8. 推荐系统。
9. 媒体健康检查。
10. NAS 状态集成。
11. 外部播放器联动。
12. 移动端 PWA。

---

## 23. 风险点

### 23.1 飞牛数据库结构变化

风险：

飞牛影视升级后数据库表结构变化。

应对：

1. 启动时 schema check。
2. 字段读取做兼容。
3. 错误提示清晰。
4. 维护数据库适配层。
5. 文档记录已适配的飞牛版本。

---

### 23.2 数据量大导致查询慢

风险：

播放记录多时报表查询慢。

应对：

1. 分页。
2. 限制默认时间范围。
3. 未来可引入报表缓存。
4. 未来可引入后台任务预计算。
5. 避免一次性加载全部数据。

---

### 23.3 误写飞牛数据库

风险：

代码错误导致飞牛原库损坏。

应对：

1. SQLite 只读连接。
2. Docker 只读挂载。
3. 禁止写入 SQL。
4. 测试覆盖写入保护。
5. Code Review 重点检查数据库连接。

---

### 23.4 外网访问安全

风险：

观看历史、用户名、媒体信息泄露。

应对：

1. 默认建议内网访问。
2. 必须登录。
3. 强密码。
4. 登录失败限制。
5. 公网访问必须 HTTPS 反代。
6. 不暴露调试接口。

---

### 23.5 前端复杂度膨胀

风险：

后台页面越来越多，前端变乱。

应对：

1. 页面按模块拆分。
2. API 按模块拆分。
3. 表格、筛选、图表抽通用组件。
4. 路由命名清晰。
5. TypeScript 类型约束。

---

## 24. 开发顺序建议

推荐顺序：

```text
Phase 0：项目准备与数据库探测
Phase 1：Docker-first 正式项目骨架
Phase 2：登录与权限
Phase 3：仪表盘
Phase 4：观看历史
Phase 5：用户管理
Phase 6：媒体库
Phase 7：报表中心
Phase 8：任务中心与缓存
Phase 9：日志中心与系统设置
Phase 10：文档、备份与 V1 发布
```

禁止顺序：

```text
先做复杂海报墙
先做多角色权限
先做通知系统
先做公网优化
先做裸机部署
先堆一个单文件 MVP
```

---

## 25. 总结

`fntv-admin` 是 Docker Compose-first 的飞牛影视增强后台。

项目核心边界：

```text
只读飞牛数据库
增强数据自管
Docker Compose-only
生产单容器优先
正式架构
分阶段实现
长期可维护
```

V1 的目标不是花哨，而是正式可用：

```text
能部署
能登录
能读数据
能看仪表盘
能查观看历史
能管用户展示
能浏览媒体库
能看基础报表
能改后台设置
能查看系统诊断
```

完成 V1 后，本项目应成为一个真正可长期扩展的 NAS 私有媒体后台，而不是一个观看历史小工具。
