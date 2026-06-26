# Docker Compose 部署

`docker-compose.yml` 是 `fntv-admin` 唯一官方生产部署入口。

## 启动

```bash
docker compose build
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

## 单容器生产模型

生产镜像通过多阶段构建完成：

1. Node 阶段构建 Vue 静态文件。
2. Python 阶段安装后端依赖。
3. 将前端 `dist` 复制到 FastAPI 静态目录。
4. 最终只运行一个 `fntv-admin` 服务容器。

