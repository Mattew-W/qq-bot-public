# QQ 对接指南

## 整体架构

```
QQ 腾讯服务器
    ↕  (QQ 协议)
NapCat（登录你的 QQ 号，模拟 QQ 客户端）
    ↕  (OneBot v11 WebSocket)
qq-bot（NoneBot2，你的项目代码）
    ↕
AI 问答 / 反垃圾 / 美团分析
```

**NapCat 是什么？** 它是一个基于 NTQQ 的无头 QQ 机器人框架，用你的 QQ 号登录后，把 QQ 消息转换成 OneBot v11 协议的 WebSocket 数据流，你的 bot 代码就能收到了。

---

## 方案一：Docker 一键部署（推荐）

### 第 1 步：准备配置

```bash
cd qq-bot
cp .env.example .env
```

编辑 `.env`，填入你的信息：

```env
# OneBot 连接（NapCat 的 WebSocket 地址）
ONEBOT_WS_URLS=["ws://napcat:3001"]

# LongCat API
LONGCAT_API_KEY=你的-longcat-api-key
```

编辑 `docker-compose.yml`，把 `你的QQ号` 改成实际 QQ 号：

```yaml
napcat:
  environment:
    - ACCOUNT=123456789  # ← 改成你的 QQ 号
```

### 第 2 步：启动

```bash
docker-compose up -d --build
```

### 第 3 步：扫码登录

```bash
# 查看 NapCat 日志，获取登录二维码
docker logs -f napcat
```

用手机 QQ 扫码登录。看到 `登录成功` 就完成了。

### 第 4 步：验证

```bash
# 检查 bot 健康
curl http://localhost:8000/health

# 打开 Web 配置 UI
浏览器访问 http://localhost:8000
```

在 QQ 群里 @机器人 试试，应该能回复了。

---

## 方案二：本地手动部署

### 第 1 步：安装 NapCat

**Windows：**

1. 下载 [NapCat](https://github.com/NapNeko/NapCatQQ/releases)
2. 解压到任意目录
3. 运行 `napcat.bat`

**Linux/Mac：**

```bash
# 使用 Docker 运行 NapCat
docker run -d \
  --name napcat \
  -e ACCOUNT=你的QQ号 \
  -e WS_URL=ws://host.docker.internal:8080 \
  -p 6099:6099 \
  mlikiowa/napcat-docker:latest
```

### 第 2 步：配置 NapCat

打开 NapCat WebUI：`http://localhost:6099`

1. 扫码登录 QQ
2. 进入「网络配置」
3. 添加 WebSocket 服务器：
   - 类型：正向 WebSocket
   - 监听地址：`0.0.0.0`
   - 端口：`3001`
   - Token：留空（或设置一个，需与 .env 中一致）

### 第 3 步：配置 bot

```bash
cd qq-bot
cp .env.example .env
```

编辑 `.env`：

```env
# 正向 WS：bot 主动连接 NapCat
ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]

# LongCat API Key
LONGCAT_API_KEY=你的-key
```

### 第 4 步：安装依赖并启动

```bash
pip install -e ".[dev]"
python bot.py
```

看到以下日志说明连接成功：

```
正在启动 NoneBot2 机器人...
机器人启动成功！正在运行...
```

---

## 方案三：Lagrange（NapCat 替代方案）

如果你不想用 NapCat，也可以用 Lagrange.Core：

1. 下载 [Lagrange](https://github.com/LagrangeDev/Lagrange.Core/releases)
2. 配置 `appsettings.json`：

```json
{
  "Port": 3001,
  "ForwardHost": "0.0.0.0",
  "Protocol": "ws"
}
```

3. 运行 Lagrange，扫码登录
4. bot 的 `.env` 同样配置 `ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]`

---

## 连接模式说明

| 模式 | 谁主动连接 | .env 配置 | NapCat 配置 |
|------|-----------|----------|------------|
| 正向 WS | bot → NapCat | `ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]` | 监听 3001 端口 |
| 反向 WS | NapCat → bot | 不需要配 WS_URLS | 连接 `ws://bot:8080/onebot/v11/ws` |

推荐用**正向 WS**，配置更简单。

---

## 常见问题

### Q: 启动后 bot 没反应？

检查连接链路：
```bash
# 1. NapCat 是否在线
docker logs napcat | grep "登录"

# 2. bot 是否收到连接
docker logs qq-bot | grep "OneBot"

# 3. WebSocket 是否通
curl http://localhost:8000/health
```

### Q: 群里 @机器人 没回复？

1. 确认 NapCat 登录的 QQ 号在群里
2. 确认 NapCat 配置了正向 WS 且端口正确
3. 确认 `.env` 中 `ONEBOT_WS_URLS` 地址正确
4. 查看 bot 日志是否收到消息：`docker logs -f qq-bot`

### Q: 提示 `LONGCAT_API_KEY` 错误？

在 `.env` 或 Web 配置 UI（http://localhost:8000）中填入正确的 LongCat API Key。

### Q: Docker 部署时 NapCat 连不上 bot？

确保两个容器在同一网络。docker-compose.yml 已经配置了 `qq-bot-net` 网络，NapCat 用 `ws://qq-bot:8080` 连接（容器名即主机名）。

### Q: NapCat 登录掉线？

QQ 风控可能导致掉线。建议：
- 用小号登录，不要用主号
- 不要频繁重启
- 保持 NapCat 版本最新
