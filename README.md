# 宁工招新群智能助手（QQ 群机器人）

宁波工程学院招新群的 QQ 群机器人。面向 **26 届新生**，@ 它就能问学校相关问题，自动基于知识库回答；同时自带反垃圾，连发刷屏 / 拉人加群的消息会直接撤回。

## 这机器人是干嘛的

- **新生答疑（AI 问答 / RAG）**：@ 机器人提问，它从 `data/knowledge/` 里的资料检索后作答。覆盖宿舍几人间、校区在哪、地理环境、转专业、食堂、生活费等问题。
- **智能反垃圾**：规则引擎 + 风险评分。同一人连发 4~5 条相似内容，或连发 3 条拉群 / 加群引流，会从第一条开始全部撤回。
- **可后台管理**：Web 配置中心看用量、知识库、反垃圾记录。

回答风格走「话少、直接、像在校学长闲聊」路线，不整 AI 那套长篇大论。

## 怎么用

| 操作 | 说明 |
|------|------|
| @机器人 + 问题 | 直接对话，例如「宿舍几人间？」 |
| `/ask <问题>` | 命令式提问 |
| `/clear` | 清除当前对话历史 |

## 技术栈

NoneBot2 + OneBot v11 + NapCat(Shell) + LongCat 2.0。SQLite 存用量与用户数据。

## 部署要点（已在本机跑通）

- QQ 机器人号：`你的QQ号`，通过 **NapCat Shell** 登录。
- 连接方式：**反向 WebSocket**。NapCat 作为 WS 客户端连到机器人，`ws://127.0.0.1:8080/onebot/v11/ws`（fastapi driver 不支持 WS 客户端，所以走反向）。
- 模型：`.env` 里 `LONGCAT_MODEL=LongCat-2.0`（大小写敏感）。
- 启动：`python bot.py`。

## 怎么更新它知道的资料

把 `.md` 文件丢进 `data/knowledge/` 即可，机器人每天凌晨 3 点自动重载；不想等就重启 `python bot.py`。

当前知识库文件：`data/knowledge/ningbo_university_of_technology.md`（学校概况、三校区地址、宿舍、转专业、食堂、地理环境等）。

## 反垃圾阈值（config/settings.py）

| 风险分 | 动作 |
|--------|------|
| < 40 | 记录日志 |
| 40~50 | LLM 二次确认 |
| ≥ 50 | 撤回 |
| ≥ 70 | 撤回 + 禁言 |
| ≥ 90 | 踢出群聊 |

连发重复 / 拉群消息命中 `RepeatRule`（score=55），直接走撤回。

## 目录结构（摘要）

```
qq-bot/
├── bot.py                  # NoneBot2 入口（挂载 FastAPI）
├── .env                    # 配置（API Key、模型、WS 地址）
├── config/settings.py      # 统一配置 + 反垃圾阈值
├── services/
│   ├── prompt_builder.py   # AI 人设与 Prompt（回答风格在这调）
│   ├── knowledge/          # 知识库（BM25 索引）
│   └── anti_spam/          # 反垃圾规则引擎
├── plugins/
│   ├── ai_qa/              # @机器人 问答
│   └── anti_spam/          # 反垃圾处置
└── data/knowledge/         # 知识库文档（机器人检索来源）
```

## 常用命令

```bash
pip install -e ".[dev]"   # 装依赖
python bot.py             # 启动
docker-compose up -d      # 或走 Docker
```

## 许可证

MIT
