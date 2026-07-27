# QQ Bot Framework

基于 **NoneBot2 + OneBot v11** 的可扩展 QQ 群机器人开发框架。

下载后只需填入 API Key、配置 OneBot 实现，即可拥有一台带 AI 问答、智能反垃圾、数据分析的 QQ 群机器人。

## 架构总览

```
QQ 用户发消息
    ↓
QQ 腾讯服务器
    ↓ (QQ 协议)
OneBot v11 实现（NapCat / Lagrange / OpenShamrock 等）
    ↓ (WebSocket)
本框架 (NoneBot2)
    ├── FastAPI 后台 ─── REST API + Web UI
    ├── 插件系统 ────── AI问答 / 反垃圾 / 数据分析
    ├── 服务层 ──────── LLM / 知识库 / 对话 / 规则引擎
    └── 数据层 ──────── SQLite (默认) / MySQL / PostgreSQL
```

## 功能一览

| 功能 | 说明 |
|------|------|
| 🤖 **AI 问答** | `@机器人 问题` 触发，知识库 RAG 检索 + 对话历史 |
| 🛡️ **智能反垃圾** | 关键词/重复/引流/广告 规则 + LLM 二次确认，自动撤回/禁言/踢人 |
| 📚 **知识库** | 丢 `.md` 文件进 `data/knowledge/` 即可，BM25 索引，凌晨自动重载 |
| 📊 **数据分析** | `/analyze 文件.csv 问题` 上传 CSV/Excel/JSON 自动分析 |
| 🌐 **Web 管理** | `http://localhost:8000` 可视化配置中心 |
| 📈 **用量统计** | 自动记录 LLM 调用、Token 消耗、延迟 |
| ⏱️ **限流保护** | 滑动窗口异步限流，防止滥用 |
| 🐳 **Docker 部署** | 一行 `docker-compose up -d` 启动 |

## 一、快速上手

### 1. 前置准备

- Python 3.11+
- 一个 QQ 机器人账号（小号即可）
- 一个 [OneBot v11 兼容实现](https://onebot.dev/ecosystem.html)（见下方推荐）

### 2. 安装

```bash
git clone https://github.com/your-username/qq-bot-framework.git
cd qq-bot-framework
python -m venv venv
source venv/bin/activate          # Linux/Mac
# 或 venv\Scripts\activate       # Windows
pip install -e ".[dev]"
```

### 3. 配置

```bash
cp .env.example .env
vim .env                          # 编辑配置
```

至少修改以下三项：

```env
# ─── LLM 配置（填入你的 API Key） ───
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
LLM_MODEL=gpt-4o-mini

# ─── OneBot 连接 ───
ONEBOT_ACCESS_TOKEN=              # 如果 OneBot 端设置了 Token，请填写
```

### 4. 启动

```bash
# 先启动你的 OneBot 实现（如 NapCat），再启动框架
python bot.py
```

看到以下输出说明启动成功：

```
INFO:     Running on http://0.0.0.0:8000
INFO:     OneBot V11 | Bot connected
```

### 5. Docker 部署

```bash
# docker-compose.yml 已包含 OneBot + 框架的组合
# 请根据你使用的 OneBot 实现修改 docker-compose.yml 中的镜像
docker-compose up -d --build
```

## 二、配置说明

所有配置在 `.env` 文件中，修改后重启生效。

### LLM 配置

```env
LLM_API_BASE=https://api.openai.com/v1    # API 地址（见下方支持列表）
LLM_API_KEY=sk-你的Key                     # API 密钥
LLM_MODEL=gpt-4o-mini                     # 模型名称
LLM_TEMPERATURE=0.7                       # 温度（0~2，越低越确定）
LLM_MAX_TOKENS=2048                        # 单次最大输出 Token
```

### OneBot 连接配置

支持两种 WebSocket 模式：

**正向 WS**（框架主动连接 OneBot）：

```env
# 在 .env 中取消注释
ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]
```

**反向 WS**（OneBot 主动连接框架，推荐）：

无需在 `.env` 中配置。只需在 OneBot 端设置反向 WS URL：

```
ws://<框架IP>:8080/onebot/v11/ws
```

### 反垃圾阈值

```env
ANTISPAM_THRESHOLD_LLM=40     # 达到此分数触发 LLM 二次确认
ANTISPAM_THRESHOLD_BAN=70     # 达到此分数自动禁言
ANTISPAM_THRESHOLD_KICK=90    # 达到此分数自动踢人
```

## 三、支持的 LLM 服务

框架通过适配器模式接入 LLM。**所有兼容 OpenAI Chat Completions API 的服务均可直接接入**，无需修改代码。

| 服务商 | 模型示例 | `LLM_API_BASE` |
|--------|---------|----------------|
| **OpenAI** | gpt-4o, gpt-4o-mini | `https://api.openai.com/v1` |
| **DeepSeek** | deepseek-chat | `https://api.deepseek.com/v1` |
| **Anthropic** | claude-3-5-sonnet | `https://api.anthropic.com/v1` |
| **Google** | gemini-1.5-pro | `https://generativelanguage.googleapis.com/v1beta/openai` |
| **通义千问** | qwen-turbo | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| **智谱 AI** | glm-4-flash | `https://open.bigmodel.cn/api/paas/v4` |
| **Moonshot** | moonshot-v1-8k | `https://api.moonshot.cn/v1` |
| **OpenRouter** | 多模型聚合 | `https://openrouter.ai/api/v1` |
| **本地部署** | Ollama / vLLM 等 | `http://localhost:11434/v1` |

切换模型只需改 `.env` 中的 `LLM_MODEL` 和 `LLM_API_BASE`。

## 四、OneBot 实现推荐

OneBot 是连接 QQ 和本框架的协议桥。请选择以下任一实现：

| 实现 | 说明 | 适用场景 |
|------|------|---------|
| **NapCat** | 基于 NTQQ，功能丰富 | 推荐，大多数场景 |
| **Lagrange.Core** | 跨平台，支持 Linux/Mac/Windows | 多平台部署 |
| **OpenShamrock** | 轻量级，易于配置 | 简单场景 |
| **LiteLoaderQQNT + llonebot** | 基于插件生态 | 已有 LL 环境 |

### NapCat 部署参考

NapCat 是一个开源的 OneBot v11 实现。

> ⚠️ 本项目与 NapCat 无隶属关系。NapCat 是社区开源项目，请遵守其 [使用协议](https://github.com/NapNeko/NapCatQQ)。

#### 方式一：Docker（推荐）

```bash
docker run -d \
  --name napcat \
  -e ACCOUNT=你的QQ号 \
  -e WS_URL=ws://宿主机IP:8080 \
  -p 6099:6099 \
  mlikiowa/napcat-docker:latest
```

#### 方式二：Windows 桌面版

1. 从 [NapCatQQ Releases](https://github.com/NapNeko/NapCatQQ/releases) 下载
2. 安装 VC++ 运行库（如遇 DLL 缺失）
3. 运行 → 扫码登录
4. 在 WebUI (`http://127.0.0.1:6099`) → OneBot11 → 网络设置 → 添加反向 WebSocket
   - URL：`ws://127.0.0.1:8080`
   - Access Token：留空（或填写你在 `.env` 中设置的值）

#### Windows 开机自启 + 实时监控（生产部署推荐）

`scripts/` 下提供一组一键脚本：把 bot 注册为 Windows 服务（无黑框、断 RDP 不死、崩溃自启），NapCat 注册为登录自启任务，并附带仿 NapCat 控制台的实时监控窗口。

| 脚本 | 作用 |
|------|------|
| `setup.bat` | 自动探测 Python 并创建 `venv`、安装依赖（无需手动配 PATH） |
| `install-all.bat` | 一键安装：QQBot → NSSM 服务；NapCat → 登录自启计划任务 |
| `install-napcat-autostart.bat` | 单独注册 NapCat 登录自启任务（如需分离安装） |
| `manage-bot.bat` | 单控 bot（停止/启动/重启/状态/实时日志），**不影响 NapCat**，便于上传更新 |
| `monitor.bat` + `bot_monitor.pyw` | 实时监控窗口：彩色日志滚动 + 服务状态 + 停/重启按钮（同 NapCat 控制台体验） |
| `uninstall-all.bat` | 卸载服务与计划任务 |
| `run_bot.bat` | 自修复启动器（NSSM 服务实际调用它）：venv 缺失自动重建、依赖缺失自动离线/联网安装 |
| `repair.bat` | 一键诊断+修复：双击自动检查并重建服务、启动，末尾 `pause` 防闪退 |
| `download_wheels.bat` | 生成离线依赖缓存（放服务器桌面 `%PUBLIC%\Desktop\wheels`，免去每次联网/整包上传带 wheels） |

**使用流程：**
1. 配置好 `.env` 后，双击 `scripts\setup.bat` 建好虚拟环境
2. 双击 `scripts\install-all.bat` 注册服务
3. 首次登录：`schtasks /run /tn "NapCatAutoStart"` → 扫码登录（仅此一次）
4. 双击 `scripts\monitor.bat` 实时查看状态

> 说明：NapCat 是 GUI 程序，不能放进 NSSM 的 Session 0，故以"仅当用户登录时运行"的计划任务启动，使二维码窗口可在桌面显示。`install-napcat-autostart.bat` 顶部的 `NAPCAT_DIR` 若与你的安装路径不同，请自行修改。

## 五、插件开发

框架基于 NoneBot2 插件系统。要添加新功能：

### 1. 创建插件目录

```bash
mkdir -p plugins/my_plugin
touch plugins/my_plugin/__init__.py
```

### 2. 编写插件

```python
# plugins/my_plugin/__init__.py
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Event, Message

my_cmd = on_command("hello")

@my_cmd.handle()
async def handle_hello(event: Event):
    await my_cmd.send("Hello from my plugin!")
```

### 3. 插件结构参考

```
plugins/
└── my_plugin/
    ├── __init__.py      # 插件入口（响应器注册）
    └── config.py        # 可选：插件专属配置
```

### 4. 获取 LLM 回复

```python
from services import get_llm_service

llm = get_llm_service()
reply = await llm.ask([
    {"role": "system", "content": "你是群助手"},
    {"role": "user", "content": "你好"}
])
```

### 5. 更多插件开发文档

- [NoneBot2 官方文档](https://nonebot.dev/)
- [OneBot v11 协议文档](https://1onebot.dev/)

## 六、项目结构

```
qq-bot/
├── bot.py                  # 启动入口
├── app.py                  # FastAPI 应用
├── .env                    # 配置文件
├── pyproject.toml          # 依赖与构建
├── adapters/               # API 适配器
│   └── llm_adapter.py      # LLM 适配器（兼容 OpenAI 格式）
├── config/
│   └── settings.py         # 配置管理（Pydantic Settings）
├── core/                   # 基础设施
│   ├── logger.py           # 日志
│   ├── cache.py            # 缓存
│   └── exceptions.py       # 自定义异常
├── database/               # 数据库
│   ├── base.py             # SQLAlchemy
│   └── models.py           # ORM 模型
├── models/                 # Pydantic 数据模型
├── plugins/                # 业务插件
│   ├── ai_qa/              # AI 问答（@机器人 提问）
│   ├── anti_spam/          # 反垃圾（规则+LLM）
│   └── analysis/           # 数据分析（/analyze 命令）
├── routers/                # API 路由
├── services/               # 业务逻辑
│   ├── llm_service.py      # LLM 统一服务
│   ├── knowledge_service.py # 知识库
│   ├── anti_spam/          # 反垃圾（规则引擎 + LLM 二次确认）
│   │   ├── rules.py         # 默认规则集（关键词/重复/引流/广告…）
│   │   ├── rules_reference.py # 参考示例：场景化自定义规则（非默认加载，可照抄）
│   │   ├── engine.py        # 规则引擎 + 风险评分 + 动作决策
│   │   └── message_tracker.py # 用户消息追踪（连带撤回用）
│   ├── action_service.py   # 动作执行
│   ├── conversation_service.py # 对话管理
│   ├── prompt_builder.py   # Prompt 构造
│   └── analysis/           # 数据分析模块
├── static/config/          # Web 配置 UI
├── data/
│   ├── knowledge/          # 知识库文件（.md）
│   └── analysis/           # 数据文件
├── scripts/                # 部署脚本
├── tests/                  # 单元测试
└── utils/                  # 工具函数
```

## 七、Web 管理界面

启动后访问 `http://localhost:8000` 打开配置中心：

- 🧠 **LLM 配置** — 修改 API Key、模型、参数
- 📡 **机器人** — OneBot 连接设置
- 🛡️ **反垃圾** — 阈值调整
- 📚 **知识库** — 分块参数
- ⚙️ **高级** — 数据库、日志、调试模式

所有修改实时保存到 `.env`，无需手动编辑。

## 八、命令一览

| 命令 | 说明 |
|------|------|
| `@机器人 问题` | 直接对话（最常用） |
| `/ask 问题` | 命令式提问 |
| `/clear` | 清除当前对话历史 |
| `/analyze 文件.csv 问题` | 数据分析 |
| `/health` | API 健康检查 |

## 九、常见问题

**Q: 启动后 OneBot 连不上？**
A: 检查 OneBot 端是否已登录、WebSocket URL 是否正确、端口是否开放。

**Q: 机器人不回复？**
A: 确认 LLM_API_KEY 正确、API Base URL 可访问、OneBot 反向 WS 已配置。

**Q: 知识库不生效？**
A: 确认文件在 `data/knowledge/` 目录，格式为 `.md` 或 `.txt`。

## 十、许可证

MIT License

## 致谢

- [NoneBot2](https://github.com/nonebot/nonebot2) — Python 异步机器人框架
- [OneBot](https://onebot.dev/) — 聊天机器人应用接口标准
- [NapCatQQ](https://github.com/NapNeko/NapCatQQ) — OneBot 实现之一
- [Lagrange.Core](https://github.com/LagrangeDev/Lagrange.Core) — OneBot 实现之一
- 以及所有兼容 OneBot v11 的开源实现
