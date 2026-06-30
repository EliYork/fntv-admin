# AGENTS.md

## 1. 项目身份

本项目名称：`fntv-admin`

本项目是一个从零开发的飞牛影视增强管理后台。

本项目不是 fork 项目，不继承任何已有项目的代码结构。其他项目只能作为需求参考，不能直接复制代码、结构或实现。

项目目标是做一个 Docker Compose-first 的 NAS 私有后台系统，提供类似 Emby 后台的管理体验。

---

## 2. 最高优先级规则

所有 AI Agent、Codex、自动化修改工具必须遵守以下规则。

### 2.1 Docker Compose 是唯一官方部署方式

本项目官方只支持 Docker Compose 部署。

不允许新增以下文档作为官方部署方式：

```text
裸机 Python 部署
裸机 Node.js 部署
PM2 部署
Nginx 手动部署
宝塔手动部署
systemd 部署
```

可以为了开发便利提供本地开发命令，但必须明确标注：

```text
仅用于开发，不是官方生产部署方式
```

---

### 2.2 生产部署优先单容器

生产环境优先使用单容器：

```text
FastAPI 后端 + Vue 构建后的静态文件
```

开发结构可以前后端分离：

```text
backend/
frontend/
```

但生产镜像应通过多阶段构建：

1. 构建前端。
2. 将前端 dist 复制到后端镜像。
3. FastAPI 托管静态文件。
4. 最终只运行一个服务容器。

---

### 2.2.1 默认部署优先 Docker Hub 成品镜像

官方 Docker Compose 部署文档默认应优先使用 Docker Hub 成品镜像：

```text
docker.io/eliyork/fntv-admin:latest
docker.io/eliyork/fntv-admin:v0.7.2
```

GHCR 作为备用镜像源：

```text
ghcr.io/eliyork/fntv-admin:latest
ghcr.io/eliyork/fntv-admin:v0.7.2
```

不要把默认镜像源改回 GHCR，不要移除 GHCR 备用发布。

飞牛 NAS 不要求本机构建镜像。

`docker-compose.yml` 默认使用 `image`。

如未来提供备用镜像 compose 文件，挂载和环境变量必须与默认 Compose 保持一致。

`docker-compose.build.yml` 仅用于开发者本地构建和测试。

不要把 `build` 作为飞牛可视化部署默认路径。

---

### 2.3 禁止写入飞牛影视数据库

飞牛影视数据库只能只读读取。

禁止对飞牛数据库执行：

```sql
INSERT
UPDATE
DELETE
DROP
ALTER
VACUUM
REINDEX
CREATE
```

除非未来文档明确修改此规则，否则任何写入飞牛数据库的代码都是严重错误。

飞牛默认 Docker Compose 中数据库目录挂载为：

```yaml
- /usr/local/apps/@appdata/trim.media/database:/fntv
```

飞牛影视实机可能使用 SQLite WAL 模式。Docker 层强制 `:ro` 可能阻止 SQLite 访问或维护 `-wal`、`-shm`、锁相关文件，导致 `unable to open database file`。默认 Compose 的 `/fntv` 挂载不加 `:ro`。

后端连接飞牛数据库时必须使用 SQLite 只读模式。

代码层必须使用 SQLite `mode=ro` 和 `PRAGMA query_only = ON`，并通过 `scripts/verify_fntv_readonly.py` 验证不写飞牛数据库。

默认直接只读读取 `/fntv/trimmedia.db`。Phase 7C 允许可选 SQLite 快照读取，但默认关闭；快照只能写入 `/data/cache/trimmedia.snapshot.db`，源库连接仍必须 `mode=ro` + `PRAGMA query_only = ON`。快照失败必须自动 fallback 到源库只读直连，不允许导致页面白屏或容器重启。

---

### 2.4 所有增强数据写入 admin.db

以下数据必须写入项目自己的 `/data/admin.db`：

```text
后台管理员账号
后台设置
主题设置
用户备注
用户别名
隐藏用户
媒体备注
隐藏媒体
收藏媒体
任务日志
操作审计
报表缓存
API Token
本地/外部访问认证策略
可选快照开关
```

禁止把这些数据写入飞牛原始数据库。

---

### 2.5 不允许临时 MVP 式堆代码

本项目不是临时 MVP。

禁止：

```text
把所有后端写进一个 main.py
把所有前端写进一个页面
为了赶进度绕过模块边界
写一次性脚本代替正式服务
跳过鉴权直接暴露业务 API
先做功能以后再重构
```

允许：

```text
页面功能先占位
API 先返回空状态
模块先搭骨架
分阶段逐步填充功能
```

原则：

```text
完整架构优先，功能分阶段实现
```

---

## 3. 项目目录约定

推荐目录：

```text
fntv-admin/
├── backend/
├── frontend/
├── docker/
├── docs/
├── scripts/
├── data/
├── docker-compose.yml
├── .env.example
├── README.md
├── AGENTS.md
└── CHANGELOG.md
```

---

## 4. 后端开发规则

### 4.1 技术栈

后端使用：

```text
Python 3.12+
FastAPI
Uvicorn
SQLAlchemy
Pydantic
SQLite
```

不应在没有明确理由的情况下更换后端框架。

---

### 4.2 后端目录

```text
backend/app/
├── main.py
├── core/
├── db/
├── models/
├── schemas/
├── services/
├── routers/
├── static/
└── utils/
```

---

### 4.3 分层规则

后端必须分层：

```text
routers：只处理 HTTP 请求和响应
services：业务逻辑
db：数据库连接和底层查询
schemas：请求和响应模型
models：admin.db ORM 模型
core：配置、日志、安全、错误处理
```

禁止在 router 中堆复杂 SQL 和业务计算。

---

### 4.4 API 响应格式

所有业务 API 应使用统一响应格式。

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
    "code": "ERROR_CODE",
    "message": "错误说明"
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

### 4.5 启动检查

后端启动时必须检查：

```text
/data 是否存在
/data 是否可写
/data/logs 是否存在
/data/cache 是否存在
/data/backup 是否存在
/fntv/trimmedia.db 是否存在
飞牛数据库是否可只读打开
飞牛数据库必要表是否存在
admin.db 是否存在
admin.db 是否需要初始化或迁移
```

如果飞牛数据库不存在，应用可以启动，但必须在系统状态中显示错误，不允许直接崩溃导致容器无限重启。

---

### 4.6 数据库连接规则

飞牛数据库连接模块：

```text
backend/app/db/fntv_readonly.py
```

要求：

1. 只读连接。
2. 独立封装。
3. 不暴露写入能力。
4. 不和 `admin.db` 复用连接。
5. 查询异常必须转换为统一错误。

admin 数据库连接模块：

```text
backend/app/db/admin_db.py
```

要求：

1. 负责 `/data/admin.db`。
2. 支持初始化。
3. 支持迁移。
4. 支持事务。
5. 只保存增强数据。

---

## 5. 前端开发规则

### 5.1 技术栈

前端使用：

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

不应在没有明确理由的情况下改成其他框架。

---

### 5.2 前端目录

```text
frontend/src/
├── main.ts
├── App.vue
├── router/
├── stores/
├── api/
├── layouts/
├── views/
├── components/
├── styles/
└── types/
```

---

### 5.3 页面规则

后台必须使用统一布局：

```text
左侧导航栏
顶部状态栏
主内容区
右侧详情抽屉
```

必须保留以下一级页面：

```text
登录
仪表盘
观看历史
用户管理
媒体库
报表中心
系统设置
系统诊断
```

任务中心和日志中心属于后续规划；当前阶段不在左侧导航暴露入口。页面可以先占位，但已暴露路由和导航必须稳定。

---

### 5.4 前端安全规则

禁止直接渲染未转义 HTML。

用户输入包括：

```text
备注
别名
搜索关键词
媒体标题
用户名
错误信息
日志片段
```

必须安全展示。

Token 或 Session 信息不得放进 URL。

业务接口返回 401 时，前端必须先复核 `/api/auth/me`。只有 `/api/auth/me` 也返回 401，才清理 Token、跳转登录并提示“请先登录”。403 应提示无权限或禁止访问，500 不能被误判为登录失效。报表等模块型页面请求失败时优先显示局部错误，不应刷屏式弹出全局错误提示。

---

## 6. Docker 规则

### 6.1 Docker Compose

`docker-compose.yml` 是官方唯一部署入口。

必须支持：

```bash
docker compose up -d
```

必须挂载：

```yaml
volumes:
  - ./data:/data
  - /usr/local/apps/@appdata/trim.media/database:/fntv
```

默认 `docker-compose.yml` 应拉取 Docker Hub 成品镜像，不默认执行本地构建。

默认镜像：

```text
docker.io/eliyork/fntv-admin:latest
docker.io/eliyork/fntv-admin:v0.7.2
```

备用 GHCR 镜像：

```text
ghcr.io/eliyork/fntv-admin:latest
ghcr.io/eliyork/fntv-admin:v0.7.2
```

Docker Hub 发布需要 GitHub Secrets `DOCKERHUB_USERNAME` 和 `DOCKERHUB_TOKEN`，其中 token 必须使用 Docker Hub access token，不要使用明文密码。

开发者本地构建必须使用：

```bash
docker compose -f docker-compose.build.yml build
docker compose -f docker-compose.build.yml up -d
```

以上命令仅用于开发，不是官方生产部署方式，也不是飞牛可视化部署默认路径。

---

### 6.2 容器路径

容器内路径固定：

```text
/fntv/trimmedia.db
/data/admin.db
/data/logs
/data/cache
/data/backup
```

不要在代码中写宿主机路径。

---

### 6.3 Dockerfile

生产 Dockerfile 必须使用多阶段构建。

基本结构：

```text
frontend-builder：构建 Vue 前端
runtime：运行 FastAPI 后端，并托管前端静态文件
```

禁止要求用户在宿主机执行：

```bash
npm install
npm run build
pip install
uvicorn
```

---

### 6.4 数据持久化

所有可变数据必须在 `/data` 下。

包括：

```text
admin.db
logs
cache
backup
```

容器删除后，只要 `/data` 保留，配置和数据就不应丢失。

---

## 7. 文档规则

### 7.1 必须维护的文档

```text
README.md
docs/DESIGN.md
docs/DOCKER_COMPOSE.md
docs/FNTV_DATABASE_PATH.md
docs/BACKUP.md
docs/UPGRADE.md
docs/FAQ.md
CHANGELOG.md
AGENTS.md
```

---

### 7.2 README 首屏要求

README 第一屏必须优先说明 Docker Compose 部署。

推荐结构：

```text
项目简介
核心特性
快速开始
docker-compose.yml 示例
飞牛数据库路径说明
默认访问地址
数据持久化说明
```

不要把裸机开发命令放在 README 第一屏。

---

### 7.3 禁止新增的官方文档

不要新增以下官方部署文档：

```text
LOCAL_INSTALL.md
PYTHON_INSTALL.md
NODE_INSTALL.md
NGINX_DEPLOY.md
PM2_DEPLOY.md
BAOTA_DEPLOY.md
```

---

## 8. 安全规则

### 8.1 认证

除以下接口外，所有 API 默认需要认证：

```text
/api/system/health
/api/auth/login
/api/auth/init-admin
```

是否允许未登录访问 `/api/system/database-status` 需要谨慎，默认应要求登录。

登录系统必须保留。可以通过系统设置配置访问策略，但默认必须安全：

```text
local_auth_required=true
remote_access_policy=login
TRUST_PROXY_HEADERS=false
```

允许本地访问在 `local_auth_required=false` 时免登录，外部访问只能默认需要登录或设置为禁止访问。不要提供外部免登录 UI，不要把所有接口改成公开无鉴权。

本地来源包括 `127.0.0.1`、`::1`、`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`fc00::/7`、`fe80::/10`。默认不信任 `X-Forwarded-For` / `X-Real-IP`；只有 `TRUST_PROXY_HEADERS=true` 时才允许使用代理头判断真实来源。

---

### 8.2 密码

管理员密码必须 hash 存储。

禁止：

```text
明文保存密码
日志输出密码
前端保存密码
把默认密码写死
```

首次启动必须引导用户创建管理员账号，或通过安全的一次性初始化方式创建。

---

### 8.3 日志

日志不能输出：

```text
密码
完整 Token
Session
敏感 Cookie
宿主机敏感路径
完整异常堆栈给前端
```

日志可以写入：

```text
/data/logs
```

---

### 8.4 外网访问

项目默认面向内网 NAS 使用。

如果文档提到公网访问，必须提醒：

```text
公网访问必须使用 HTTPS 反向代理
必须使用强密码
必须限制登录失败频率
不要直接暴露未加保护的管理后台
```

---

## 9. 开发阶段规则

### 9.1 Phase 0

只做：

```text
项目目录
设计文档
AGENTS.md
Docker Compose 草案
数据库探测脚本
飞牛数据库结构报告
```

不要做复杂业务页面。

---

### 9.2 Phase 1

只做：

```text
FastAPI 骨架
Vue 骨架
多阶段 Dockerfile
Docker Compose 启动
前端静态文件托管
健康检查
数据库状态检查
admin.db 初始化
页面占位
```

不要做复杂统计和图表。

---

### 9.3 Phase 2

做：

```text
登录
退出
首次初始化管理员
路由守卫
API 鉴权
修改密码
登录日志
基础审计
```

---

### 9.4 Phase 3 以后

按顺序做：

```text
仪表盘
观看历史
用户管理
媒体库
报表中心
系统设置
系统诊断
文档和 V1 发布
```

任务中心和日志中心后续再做；不要跳到复杂 V2 功能。

---

## 10. 禁止事项

严禁：

```text
写入飞牛数据库
移除 Docker Compose-only 定位
把生产部署改成多容器复杂方案，除非有明确理由
增加裸机部署作为官方推荐
把所有代码堆进单文件
跳过登录鉴权
未登录暴露观看历史
直接拼接未转义 HTML
在日志里输出敏感信息
将 /data 内生成文件提交到 Git
提交真实 admin.db
提交真实 trimmedia.db
提交真实日志
```

---

## 11. Git 忽略规则建议

`.gitignore` 应包含：

```gitignore
data/*
!data/.gitkeep

*.db
*.sqlite
*.sqlite3

logs/
*.log

cache/
backup/

.env
.env.local

node_modules/
dist/

__pycache__/
*.pyc
.venv/
venv/

.DS_Store
Thumbs.db
```

---

## 12. 测试要求

### 12.1 最低测试要求

每次修改后至少验证：

```text
docker compose pull 或 docker compose config 成功
docker compose up -d 成功
/api/system/health 正常
前端页面可打开
/data/admin.db 可创建
飞牛数据库不存在时不崩溃
飞牛数据库源库可通过 SQLite mode=ro 只读打开
```

如需验证本地构建，只能使用：

```text
docker compose -f docker-compose.build.yml build 成功
```

---

### 12.2 飞牛数据库写入保护测试

必须有测试或脚本验证：

```text
飞牛数据库连接为只读
写入 SQL 会失败
Docker Compose 默认挂载飞牛数据库目录到 /fntv，飞牛 WAL 场景下不强制 :ro
代码中没有对 fntv 连接执行写入操作
```

---

### 12.3 前端最低验证

至少验证：

```text
登录页可访问
后台布局可访问
导航跳转正常
API 错误能展示
数据库异常能展示
移动端不严重错位
```

---

## 13. 代码风格

### 13.1 后端

要求：

```text
类型标注
清晰函数命名
模块职责单一
避免超长函数
SQL 参数化
统一异常处理
```

禁止：

```text
字符串拼接 SQL 参数
在 router 中写大量业务逻辑
吞掉异常不记录
返回不统一结构
```

---

### 13.2 前端

要求：

```text
TypeScript 类型
API 模块化
组件拆分
路由清晰
表格和筛选可复用
状态管理清晰
```

禁止：

```text
大量 any
重复请求逻辑
页面里堆超长函数
直接操作 DOM 拼接危险 HTML
```

---

## 14. UI 设计方向

整体风格：

```text
清爽
现代
后台管理感
信息密度适中
适合桌面端
兼顾平板和手机
```

主题：

```text
浅色
深色
后续可加浅粉主题
```

默认不要使用过重、过暗、过花的视觉风格。

---

## 15. 给 AI Agent 的工作方式

每次任务开始前必须先判断当前阶段。

输出修改前计划：

```text
本次目标
涉及文件
不涉及内容
风险点
验证方式
```

修改后输出：

```text
修改文件列表
实现内容
未完成内容
验证结果
风险点
下一步建议
```

如果任务涉及数据库，必须额外说明：

```text
是否读取飞牛数据库
是否写入飞牛数据库
是否写入 admin.db
如何保证飞牛数据库只读
```

---

## 16. 推荐首轮提示词

```text
模型档位：high

我要从零开发 fntv-admin，不 fork 任何已有仓库。

请严格遵守 AGENTS.md。

项目定位：
Docker Compose-first 的飞牛影视增强管理后台。

最高优先级规则：
1. 官方只支持 Docker Compose 部署。
2. 生产部署优先单容器。
3. 开发结构前后端分离。
4. 前端 Vue 3 + Vite + TypeScript。
5. 后端 FastAPI。
6. 使用多阶段 Dockerfile。
7. FastAPI 托管前端构建后的静态文件。
8. 飞牛数据库目录挂载到 /fntv，后端通过 SQLite mode=ro 只读打开 /fntv/trimmedia.db。
9. 项目数据统一写入 /data。
10. 所有增强数据写入 /data/admin.db。
11. 禁止写入飞牛影视数据库。
12. 不提供裸机部署文档。
13. 不做临时 MVP 式单文件堆代码。

本轮只做 Phase 0 和 Phase 1。

Phase 0：
- 创建项目目录
- README.md
- docs/DESIGN.md
- AGENTS.md
- .env.example
- docker-compose.yml
- scripts/inspect_fntv_db.py

Phase 1：
- 初始化 FastAPI 后端骨架
- 初始化 Vue 前端骨架
- 建立多阶段 Dockerfile
- Docker Compose 可启动
- 后端提供 /api/system/health
- 后端提供 /api/system/database-status
- 后端启动时检查 /data 和 /fntv/trimmedia.db
- 初始化 /data/admin.db
- 前端提供登录页占位和后台布局占位
- 前端页面包括：仪表盘、观看历史、用户管理、媒体库、报表中心、系统设置
- 系统诊断页包括：飞牛数据库状态、schema 诊断、只读状态、复制诊断信息
- Phase 7C 可增加：快照状态、播放时段分布、最近活跃观看推断、收藏记录只读列表、下载记录只读诊断、watched 字段诊断
- 不实现复杂业务查询
- 不实现复杂图表
- 不写入飞牛数据库

输出：
1. 修改文件列表
2. 项目结构
3. 如何 docker compose 启动
4. 如何验证飞牛数据库没有被写入
5. 当前风险点
6. 下一阶段建议
```

---

## 17. 最终判断标准

一个修改是好的，当且仅当它同时满足：

```text
不破坏 Docker Compose-only 定位
不写入飞牛数据库
不污染 /data 之外的路径
不把架构退回单文件小工具
不跳过登录和权限边界
不引入不必要的部署复杂度
能被长期维护
```

如果为了快速完成某个功能而违反以上规则，应拒绝该实现并重新设计。
