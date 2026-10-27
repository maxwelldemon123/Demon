# dsh-demon 0.1.0

本地记忆 / 情绪服务，给 Demon 和酒馆插件用。

## 运行

```powershell
npm install
npm start          # 监听 127.0.0.1:8791
```

首次启动生成：

```
%LOCALAPPDATA%\dsh-demon\token
%LOCALAPPDATA%\dsh-demon\memory.sqlite
```

## 环境变量

| 变量 | 默认 |
| --- | --- |
| `DSH_DEMON_PORT` | 8791 |
| `DSH_DEMON_DATA` | `%LOCALAPPDATA%\dsh-demon` |
| `DSH_DEMON_ST_DATA` | `C:/mylove/SillyTavern/data/default-user` |
| `DSH_DEMON_SCAN_MS` | 60000 |

## 接口

```
GET  /v1/health
GET  /v1/stats
POST /v1/memory/append
POST /v1/memory/query
GET  /v1/state/emotion
POST /v1/state/emotion
POST /v1/events
GET  /v1/chat/messages
WS   /v1/events?token=...
```

除 `/v1/health` 外都要 `X-Dsh-Token`。

## 扫描

- 启动时全量扫描聊天与世界书
- 每 60 秒增量扫描聊天
- 每 5 分钟扫描世界书 / 角色卡（只记 hash）
