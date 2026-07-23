# 部署文档

## 快速部署

### 1. 前置要求

- Python 3.11+
- OneBot v11 兼容实现 (NapCat / Lagrange.OneBot / OpenShamrock 等)
- 一个 QQ 机器人账号

### 2. 本地部署

```bash
# 克隆项目
git clone https://github.com/your-username/qq-bot-framework.git
cd qq-bot-framework

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[dev]"

# 配置 .env
cp .env.example .env
vim .env  # 填入你的配置

# 启动
python bot.py
```

### 3. Docker 部署

```bash
# 先配置 .env，然后
docker-compose up -d --build
```

## 目录结构

```
qq-bot/
├── bot.py                  # NoneBot2 入口（挂载 FastAPI）
├── app.py                  # FastAPI 应用实例
├── .env                    # 配置（API Key、模型、WS 地址）
├── pyproject.toml          # 项目配置
├── adapters/               # 第三方 API 适配器
│   └── llm_adapter.py      # LLM API 适配器 (兼容 OpenAI 格式)
├── config/
│   └── settings.py         # 统一配置管理 (Pydantic Settings)
├── core/                   # 基础设施
│   ├── logger.py           # 日志 (Loguru)
│   ├── cache.py            # 缓存
│   └── exceptions.py       # 自定义异常
├── database/               # 数据库
│   ├── base.py             # SQLAlchemy 引擎 + 会话
│   └── models.py           # ORM 模型
├── models/                 # Pydantic 模型 (API 请求/响应)
├── plugins/                # NoneBot2 插件 (业务功能)
│   ├── ai_qa/              # AI 问答插件
│   └── anti_spam/          # 反垃圾插件
├── routers/                # FastAPI 路由
│   ├── config.py           # 配置管理 API
│   ├── knowledge.py        # 知识库 API
│   ├── llm.py              # LLM 用量 API
│   └── dashboard.py        # 仪表盘 API
├── services/               # 业务逻辑层
│   ├── llm_service.py      # LLM 服务
│   ├── knowledge_service.py # 知识库服务
│   ├── anti_spam_service.py # 反垃圾服务
│   ├── action_service.py   # 动作执行服务
│   ├── conversation_service.py # 对话管理
│   ├── prompt_builder.py   # Prompt 构造器
│   └── analysis/           # 数据分析模块
├── static/config/          # Web 配置中心 UI
├── data/
│   ├── knowledge/          # 知识库文件 (.md)
│   └── analysis/           # 数据文件
└── scripts/                # 部署脚本
```

## 端口

| 端口 | 用途 |
|------|------|
| `8000` | FastAPI 管理接口 + Web UI |
| `8080` | OneBot WebSocket 反向连接 |

## OneBot 连接模式

### 正向 WebSocket（推荐）

NoneBot 主动连接 OneBot 实现：

```env
# .env 中配置
ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]
```

OneBot 端需开启 WebSocket 服务器，监听 3001 端口。

### 反向 WebSocket

OneBot 实现主动连接 NoneBot：

无需在 .env 中配置，只需在 OneBot 端配置反向 WS URL：
`ws://<服务器IP>:8080/onebot/v11/ws`

## 升级

```bash
git pull
docker-compose up -d --build  # 或重启 python bot.py
```

## 备份

```bash
# 备份数据库
docker exec qq-bot sqlite3 /app/data/qqbot.db ".dump" > backup.sql
```

## 常见问题

### 1. 机器人不响应

- 检查 OneBot 端是否正常登录
- 检查 WebSocket URL 和 Token 是否正确
- 查看日志：`docker-compose logs -f qq-bot`

### 2. 知识库不加载

- 确认知识库文件在 `data/knowledge/` 目录
- 支持 `.md`、`.txt` 格式
- 调用重载接口：`curl -X POST http://localhost:8000/api/knowledge/reload`

### 3. LLM 调用失败

- 检查 `LLM_API_KEY` 是否正确
- 检查网络连通性
- 确认 API Base URL 格式正确（需包含 `/v1`）

### 4. Docker 部署时 OneBot 连不上 bot？

确保两个容器在同一网络。docker-compose.yml 已经配置了 `bot-net` 网络，OneBot 用 `ws://qq-bot:8080` 连接（容器名即主机名）。
