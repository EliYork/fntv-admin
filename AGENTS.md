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
docker.io/eliyork/fntv-admin:vX.Y.Z
```

GHCR 作为备用镜像源：

```text
ghcr.io/eliyork/fntv-admin:latest
ghcr.io/eliyork/fntv-admin:vX.Y.Z
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

源库固定通过 SQLite `mode=ro` + `PRAGMA query_only = ON` 只读读取 `/fntv/trimmedia.db`。SQLite 快照读取默认开启，默认每 15 分钟按需自动刷新；快照只能写入 `/data/cache/trimmedia.snapshot.db`。`admin.db` 中用户已保存的快照开关和刷新间隔永远优先于项目默认，缺少的设置键才使用当前默认。快照失败必须自动 fallback 到源库只读直连，不允许导致页面白屏或容器重启。

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
顶部状态栏
单页数据中心主内容区
设置 / 功能抽屉
按需使用的详情抽屉
```

当前产品不使用固定左侧导航栏。日常高频信息集中在单页数据中心，设置、诊断和其他低频功能通过顶部入口统一收纳到功能抽屉；不得因传统后台布局习惯恢复固定侧栏。

媒体库一级列表采用顶层媒体视图，不平铺 Series 下的 Season / Episode；电视剧按 `Series → Season → Episode` 层级浏览，并按需读取直接子级。

必须保留以下一级页面：

```text
登录
仪表盘
观看历史
用户管理
媒体库
系统设置
系统诊断
```

任务中心和日志中心属于后续规划；当前阶段不在功能抽屉暴露入口。页面可以先占位，但已暴露路由和功能入口必须稳定。

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
docker.io/eliyork/fntv-admin:vX.Y.Z
```

备用 GHCR 镜像：

```text
ghcr.io/eliyork/fntv-admin:latest
ghcr.io/eliyork/fntv-admin:vX.Y.Z
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

## 12. 验证与验收

### 12.1 AI Agent 只负责开发侧技术验证

AI Agent 完成修改后，只需要根据本次任务实际影响范围做必要的开发侧技术检查，不要求为了“证明完成”执行与任务无关的全套验收。

验证按以下大类选择：

```text
构建与静态检查
自动化测试
API / 数据契约检查
Docker / 配置检查
数据库与安全边界检查
必要的基础 Smoke（冒烟测试）
```

原则：

- 修改前端时，优先确认 TypeScript / build 和受影响功能没有明显技术错误。
- 修改后端时，优先确认相关测试、接口和异常处理正常。
- 修改 Docker、配置或部署逻辑时，再检查对应 Compose / 构建链路。
- 修改飞牛数据库读取、Schema 适配、查询或时间处理时，必须额外确认只读边界和相关数据逻辑。
- 不要求每次任务都启动完整生产环境，也不要求为了形式重复执行与本次修改无关的检查。

开发侧检查通过，只能说明“技术检查通过”，不能等同于产品最终验收。

---

### 12.2 最终成果由用户亲自验收

以下内容默认由用户在真实使用环境中亲自验收：

```text
页面视觉效果
布局与信息层级
交互手感
移动端实际体验
真实飞牛数据是否符合预期
时间、时区、播放记录等实机表现
产品是否达到用户想要的最终效果
```

AI Agent 不得仅凭自己的截图、自动化测试、Smoke、模拟数据或代码阅读宣布这些内容“验收通过”。

如果尚未经过用户实际确认，应明确写：

```text
待用户实机验收
```

允许 AI Agent 为开发需要启动页面、查看截图、调用 API 或做运行时检查，但这些只属于开发侧验证，不代表替用户完成最终验收。

---

### 12.3 飞牛数据库安全验证

飞牛数据库只读属于项目硬性安全边界，不受“用户最终验收”规则影响。

凡是修改涉及飞牛数据库连接、查询、Schema 适配、快照或数据读取链路，必须确认：

```text
源数据库仍通过 SQLite 只读方式访问
代码没有新增对飞牛数据库的写入路径
增强数据仍只写入 /data/admin.db 或 /data 下允许的位置
```

必要时使用项目现有只读验证脚本或相关自动化测试。

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

AI Agent 以**成果导向**为主，不要为了过程完整而输出大量步骤噪音。

### 15.1 开始任务时

先理解本次任务的：

```text
目标成果
关键约束
涉及范围
明确不应改动的内容
```

优先审计现有实现并复用已有架构。除非任务复杂、跨系统或高风险，否则不需要输出冗长的修改前计划。

---

### 15.2 实现时

围绕用户要的最终成果自行判断合理实现方式。

原则：

- 优先解决真实问题，不为完成 checklist 制造无意义改动。
- 不把任务拆成过细步骤后逐条机械执行。
- 不因为方便验收而加入用户没有要求的 UI、日志、调试入口或说明文字。
- 发现任务描述与现有架构冲突时，应基于项目规则选择更稳妥方案，并在交付时说明。
- 遇到真实不确定性可以做开发侧验证，但不要把验证过程本身当成主要成果。

---

### 15.3 完成后汇报

交付报告以结果为主，通常包含以下大类即可：

```text
完成的成果
主要修改文件
开发侧技术检查结果
未解决问题或风险
需要用户实机验收的内容
```

如果任务涉及数据库，额外说明：

```text
是否读取飞牛数据库
是否写入飞牛数据库
是否写入 admin.db
只读边界是否保持
```

不要输出冗长的逐步操作记录，除非用户明确要求。

---

### 15.4 AI Agent 不负责最终验收

AI Agent 可以确认：

```text
build 通过
类型检查通过
自动化测试通过
API Smoke 通过
只读保护检查通过
```

但在没有用户实际确认前，不得自行宣称：

```text
页面效果验收通过
交互体验验收通过
真实数据完全正确
时间显示完全正确
移动端体验验收通过
项目成果已最终验收
```

这些最终成果由用户亲自验收。

Agent 完成开发后，应把需要实际体验确认的部分标记为：

```text
待用户实机验收
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
- 前端页面包括：仪表盘、观看历史、用户管理、媒体库、系统设置
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

以上标准属于项目级技术与架构判断；具体功能、视觉、交互和真实数据表现是否达到最终预期，由用户亲自验收。AI Agent 不得以自身开发侧验证代替用户最终验收。

---

## 18. Git 分支、开发与发布纪律

### 18.1 正式分支模型

项目采用：

```text
develop -> main -> version tag
```

`develop` 用于所有日常开发、Agent 修改、Bug 修复、新功能、UI 调整、文档开发和开发侧测试。普通开发默认只能在 `develop` 进行；push 后自动构建 Docker Hub 与 GHCR 的 `:dev` 镜像。

`main` 只接收已经由用户本人在真实 NAS 环境验收、并明确确认准备正式发布的代码；push 后自动构建 Docker Hub 与 GHCR 的 `:latest` 镜像。普通开发 Agent 不得直接在 `main` 开发、push `main`，也不得自行决定将 `develop` 合并到 `main`。

正式 version tag 只用于稳定版本，格式为 `vMAJOR.MINOR.PATCH`，且必须指向正式 `main` 历史中的 commit。已经发布的 tag 不得删除、移动、force 更新或改指其他 commit；修复必须发布新版本。

### 18.2 开发开始前 Git 检查

每次开始正式修改前至少确认：

```text
当前 branch
git status
当前 HEAD
是否存在用户未提交修改
本地 develop 与 origin/develop 是否存在明显分叉
```

日常开发任务如果当前不在 `develop`，应先判断切换是否安全。不得为了切换分支或方便开发执行 `git reset --hard`、`git clean`、覆盖用户修改、丢弃用户文件或强制恢复整个工作区。用户修改与任务文件重叠时必须谨慎合并，并在交付报告中说明。

### 18.3 开发完成后 commit 与 push

除非用户明确要求“不要 commit”“不要 push”“只审计”“只查看”或“只给建议”，一个可交付开发任务默认包含：

1. 完成与影响范围相符的开发侧技术检查。
2. 检查 diff 与最终 Git 状态。
3. 确认没有误提交数据库、日志、Secrets、`.env`、构建产物或其他运行时文件。
4. 在 `develop` 创建清晰 commit。
5. 立即 push 到 `origin/develop`。

不要把已经完成的任务长期留在未提交状态，也不要把本地 commit 表述成“已推送”。

### 18.4 Commit 规范

Commit message 使用清晰、简短的 Conventional Commit 风格，例如：

```text
feat: add automated release workflow
fix: make host port configurable
docs: document develop release workflow
chore: harden release automation
```

禁止使用 `update`、`changes`、`fix stuff`、`123` 等无意义 message。一个任务通常使用一个完整 commit；仅在成果天然独立时合理拆分，不为制造形式上的历史而拆成大量微型 commit。

### 18.5 Push 冲突处理

普通开发 push 目标为 `origin/develop`。禁止 force push，包括 `git push --force` 和 `git push --force-with-lease`，除非用户在本次任务中明确授权。

如果 push 因远端 `develop` 有新提交而被拒绝，应先确认工作区和本地 commit 安全，再执行：

```bash
git pull --rebase origin develop
```

如果 rebase 出现冲突，停止自动推进，保留现场并报告。不得擅自选择冲突一方、覆盖远端代码、重写他人历史或用 force push 绕过冲突。

### 18.6 正式发布边界

普通开发 Agent 不负责 merge `main`、创建正式 tag 或 GitHub Release，除非用户在当前任务中明确要求执行正式发布。正式发布顺序为：

```text
develop 完成开发
-> 用户在 NAS 使用 :dev 实机验收
-> 用户确认 develop 合并到 main
-> main 自动构建 :latest
-> 从 main 运行 Release workflow 并输入 vMAJOR.MINOR.PATCH
-> 自动创建不可变 tag
-> 自动构建 Docker Hub / GHCR version 镜像
-> 自动创建 GitHub Release 与校验文件
```

用户本人也可以 push 合法且属于 `main` 历史的 version tag 来触发相同正式 Release 流程。普通开发任务不得创建 version tag、发布 GitHub Release、移动旧 tag 或覆盖旧 Release。

### 18.7 交付报告 Git 信息

完成开发后的交付报告必须说明：

```text
当前 branch
最终 commit SHA
commit message
是否成功 push
push 目标分支
关键技术检查结果
待用户实机验收项
```

如果 push 未成功，必须明确说明原因和当前本地状态。
