# QQ Bot Framework

基于 NoneBot2 + OneBot v11 的可扩展 QQ 群机器人框架。

本框架提供了一套完整的 QQ 群机器人开发脚手架，开发者可基于此框架快速构建自己的群聊天机器人，无需从零搭建基础设施。

## 架构设计

```
QQ 腾讯服务器
    ↕  (QQ 协议)
OneBot 实现 (NapCat / Lagrange / OpenShamrock / ...)
    ↕  (OneBot v11 WebSocket)
qq-bot-framework (NoneBot2)
    ├── FastAPI 管理后台 (端口 8000)
    │   ├── REST API
    │   ├── Web 配置中心 UI
    │   └── 健康检查
    │
    ├── 插件层 (Plugins)
    │   ├── AI 问答 (RAG)
    │   ├── 反垃圾
    │   └── 数据分析
    │
    ├── 服务层 (Services)
    │   ├── LLM 服务 (多模型适配)
    │   ├── 知识库服务 (BM25 索引)
    │   ├── 反垃圾服务 (规则引擎)
    │   ├── 对话管理
    │   └── 动作执行
    │
    ├── 数据层 (Database)
    │   ├── SQLAlchemy ORM
    │   ├── SQLite (默认)
    │   └── 可扩展至 MySQL/PostgreSQL
    │
    └── 适配器层 (Adapters)
        └── LLM API (兼容 OpenAI 格式)
```

### 核心设计原则

- **配置与代码分离**：所有配置通过 `.env` 文件管理，零硬编码
- **插件化架构**：功能以 NoneBot2 插件形式组织，按需启用
- **服务层抽象**：业务逻辑封装在 Service 层，便于单元测试和复用
- **适配器模式**：LLM 接入采用适配器模式，支持任意兼容 OpenAI API 的模型

## 核心功能

| 功能 | 说明 |
|------|------|
| **AI 问答 (RAG)** | @机器人 提问，自动从知识库检索后回答。支持对话历史上下文 |
| **智能反垃圾** | 规则引擎 + 风险评分 + LLM 二次确认。支持撤回、禁言、踢人 |
| **知识库管理** | 支持 Markdown/纯文本，BM25 全文索引，定时自动重载 |
| **对话管理** | 自动记录对话历史，支持 `/clear` 清除，按用户/群隔离 |
| **Web 配置中心** | 可视化配置管理，实时修改 API Key、模型参数、阈值等 |
| **用量统计** | 自动记录 LLM 调用次数、Token 消耗、延迟等 |
| **数据分析** | 支持 CSV/Excel/JSON 上传，AI 驱动的数据分析 |
| **图片 OCR** | 支持图片消息 OCR 识别（需 OneBot 实现支持） |
| **限流保护** | 基于滑动窗口的异步限流，防止滥用 |
| **Docker 部署** | 支持 Docker Compose 一键部署 |

## 支持的 AI 模型

本框架通过适配器模式接入 LLM，**所有兼容 OpenAI Chat Completions API 的模型服务均可接入**：

### 已验证支持的模型/服务

| 服务商 | 模型示例 | API Base URL |
|--------|---------|-------------|
| **OpenAI** | gpt-4o, gpt-4o-mini, o1-preview | `https://api.openai.com/v1` |
| **DeepSeek** | deepseek-chat, deepseek-coder | `https://api.deepseek.com/v1` |
| **Anthropic** | claude-3-5-sonnet, claude-3-opus | `https://api.anthropic.com/v1` |
| **Google** | gemini-1.5-pro, gemini-2.0-flash | `https://generativelanguage.googleapis.com/v1beta/openai` |
| **通义千问** | qwen-turbo, qwen-plus, qwen-max | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| **智谱 AI** | glm-4, glm-4-flash | `https://open.bigmodel.cn/api/paas/v4` |
| **Moonshot** | moonshot-v1-8k, moonshot-v1-32k | `https://api.moonshot.cn/v1` |
| **OpenRouter** | 多模型聚合 | `https://openrouter.ai/api/v1` |
| **本地部署** | Ollama, vLLM, LocalAI 等 | 自定义地址 |

### 接入方式

#### 1. 通过 .env 文件配置

```env
# LLM 配置
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-your-api-key
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
```

#### 2. 通过 Web 配置中心

启动后访问 `http://localhost:8000`，在 "LLM 配置" 标签页中修改。

#### 3. 通过 API 动态修改

```bash
curl -X PUT http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"LLM_API_KEY":"sk-new-key","LLM_MODEL":"gpt-4o"}'
```

### 切换模型示例

**切换到 DeepSeek：**
```env
LLM_API_BASE=https://api.deepseek.com/v1
LLM_API_KEY=sk-deepseek-key
LLM_MODEL=deepseek-chat
```

**切换到通义千问：**
```env
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=sk-dashscope-key
LLM_MODEL=qwen-turbo
```

**切换到本地 Ollama：**
```env
LLM_API_BASE=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=llama3
```

## 快速开始

### 1. 前置要求

- Python 3.11+
- OneBot v11 兼容实现 (NapCat / Lagrange.OneBot / OpenShamrock 等)
- 一个 QQ 机器人账号

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
vim .env  # 填入你的 LLM_API_KEY 和其他配置
```

### 4. 启动

```bash
python bot.py
```

### 5. Docker 部署

```bash
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

## 反垃圾阈值

| 风险分 | 动作 |
|--------|------|
| < 40 | 记录日志 |
| 40~50 | LLM 二次确认 |
| ≥ 50 | 撤回 |
| ≥ 70 | 撤回 + 禁言 |
| ≥ 90 | 踢出群聊 |

## 常用命令

```bash
pip install -e ".[dev]"   # 装依赖
python bot.py             # 启动
docker-compose up -d      # 或走 Docker
```

## 许可证

MIT
