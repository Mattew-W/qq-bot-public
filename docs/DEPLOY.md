# 部署文档

## 快速部署

### 1. 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- QQ 机器人账号 (在 [NapCat](https://github.com/NekoX-Dev/NapCatQQ) 或 Lagrange 中配置)

### 2. 配置

```bash
# 克隆项目
git clone <repository-url>
cd qq-bot

# 编辑配置
cp .env.example .env
vim .env
```

需要配置的关键项：

| 变量 | 说明 | 示例 |
|------|------|------|
| `BOT_APP_ID` | 机器人应用 ID | `123456789` |
| `LONGCAT_API_KEY` | LongCat API Key | `sk-xxxxx` |
| `ONEBOT_WS_URL` | OneBot WebSocket 地址 | `ws://127.0.0.1:8080` |

### 3. 启动

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f qq-bot
```

### 4. 验证

```bash
# 健康检查
curl http://localhost:8000/health

# 仪表盘
curl http://localhost:8000/api/dashboard/stats
```

## 目录结构

```
/data/qqbot.db    # SQLite 数据库
/logs/            # 日志文件 (按天切分)
/data/knowledge/  # 知识库文件
/data/meituan/    # 美团数据文件
```

## 端口

| 端口 | 用途 |
|------|------|
| `8000` | FastAPI 管理接口 |
| `8080` | OneBot WebSocket |

## 升级

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

## 备份

```bash
# 备份数据库
docker exec qq-bot sqlite3 /app/data/qqbot.db ".dump" > backup.sql

# 恢复
docker exec -i qq-bot sqlite3 /app/data/qqbot.db < backup.sql
```

## 常见问题

### 1. 机器人不响应

- 检查 OneBot 适配器是否正确配置
- 检查 WebSocket URL 和 Token 是否正确
- 查看日志：`docker-compose logs -f qq-bot`

### 2. 知识库不加载

- 确认知识库文件在 `data/knowledge/` 目录
- 支持 `.md`、`.txt` 格式
- 调用重载接口：`curl -X POST http://localhost:8000/api/knowledge/reload`

### 3. LLM 调用失败

- 检查 `LONGCAT_API_KEY` 是否正确
- 检查网络连通性
- 查看 LLM 使用记录：`curl http://localhost:8000/api/llm/usage`
