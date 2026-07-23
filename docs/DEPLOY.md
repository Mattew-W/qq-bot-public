# 部署指南

## 本地部署

### 1. 前置要求

- Python 3.11+
- OneBot v11 兼容实现（NapCat / Lagrange.OneBot / OpenShamrock 等）

### 2. 安装

```bash
git clone https://github.com/your-username/qq-bot-framework.git
cd qq-bot-framework
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

### 3. 配置

```bash
cp .env.example .env
vim .env  # 填入 LLM_API_KEY 和 OneBot 配置
```

### 4. 启动

先启动 OneBot 实现，再启动框架：

```bash
python bot.py
```

## Docker 部署

```bash
# docker-compose.yml 已包含 OneBot + 框架的组合
docker-compose up -d --build
```

## 端口

| 端口 | 用途 |
|------|------|
| `8000` | FastAPI 管理接口 + Web UI |
| `8080` | OneBot WebSocket 反向连接 |

## 升级

```bash
git pull
# 本地部署：重启 python bot.py
# Docker：
docker-compose up -d --build
```

## 备份

```bash
# 备份数据库
sqlite3 data/qqbot.db ".dump" > backup.sql
```

## 常见问题

### 机器人不响应

- 检查 OneBot 端是否正常登录
- 检查 WebSocket URL 和 Token 是否正确
- 查看日志：`docker-compose logs -f qq-bot`

### 知识库不加载

- 确认知识库文件在 `data/knowledge/` 目录
- 支持 `.md`、`.txt` 格式
- 调用重载接口：`curl -X POST http://localhost:8000/api/knowledge/reload`

### LLM 调用失败

- 检查 `LLM_API_KEY` 是否正确
- 检查网络连通性
- 确认 API Base URL 格式正确（需包含 `/v1`）
