# Docker Compose 部署

`docker-compose.yml` 是 `fntv-admin` 唯一官方生产部署入口。

飞牛 NAS 推荐使用 GHCR 成品镜像，不推荐在飞牛本机 build。默认 `docker-compose.yml` 使用 `image` 拉取镜像。

## 启动

```bash
docker compose up -d
```

访问：

```text
http://localhost:8080
```

## 必需挂载

```yaml
volumes:
  - ./data:/data
  - /path/to/trimmedia.db:/fntv/trimmedia.db:ro
```

飞牛影视数据库挂载必须保留 `:ro`，后台只读读取该数据库。`./data` 保存 `admin.db`、日志、缓存和备份。

## 镜像地址

默认镜像地址格式：

```text
ghcr.io/<GitHub 用户名或组织名>/fntv-admin:latest
```

使用前把 `docker-compose.yml` 中的 `REPLACE_WITH_YOUR_GITHUB_USERNAME` 替换为自己的 GitHub 用户名或组织名。

## 单容器生产模型

生产镜像通过多阶段构建完成：

1. Node 阶段构建 Vue 静态文件。
2. Python 阶段安装后端依赖。
3. 将前端 `dist` 复制到 FastAPI 静态目录。
4. 最终只运行一个 `fntv-admin` 服务容器。

## 开发者本地构建

以下命令仅用于开发者本地测试，不是官方生产部署方式，也不是飞牛可视化部署默认路径：

```bash
docker compose -f docker-compose.build.yml build
docker compose -f docker-compose.build.yml up -d
```
