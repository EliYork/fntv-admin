# 飞牛数据库结构报告

当前仓库不包含真实飞牛影视数据库样本，因此本文件记录探测方式和适配策略。

## 探测命令

```bash
python scripts/inspect_fntv_db.py /path/to/trimmedia.db --json
```

该脚本使用 SQLite `mode=ro` 打开数据库，只读取表和字段信息，不执行任何写入。

## 当前适配策略

后端启动时会尝试识别以下候选表：

- 用户表：表名包含 `user`、`account`、`member`。
- 媒体表：表名包含 `item`、`media`、`video`、`movie`、`episode`。
- 播放表：表名包含 `play`、`history`、`watch`、`progress`。

识别失败时，API 返回空状态或数据库异常信息，前端不会白屏，容器也不会因为缺失飞牛数据库而无限重启。

