# 架构（2026-10-26 定稿）

## 三方

```
酒馆端 smartdemon ──HTTP──> Demon (8790) ──HTTP/WS──> dsh-demon (8791)
                                   │
                                   ├─ Live2D: vts-obs模式 / 本地桌宠
                                   └─ 语音: TTS / ASR / 七情绪
```

| 组件 | 职责 | 数据 |
| --- | --- | --- |
| smartdemon | 聊天 UI、逐句朗读、角色绑定入口 | 无长期存储 |
| Demon | 身体：语音、Live2D、情绪感知、设备 | 配置、音色、短缓存 |
| dsh-demon | 大脑：记忆、情绪存档、摘要、世界书只读同步 | `%LOCALAPPDATA%\dsh-demon\memory.sqlite` |

## 记忆分层

| 数据 | 源 | 副本 | 规则 |
| --- | --- | --- | --- |
| 世界书 / 角色卡 | 酒馆 | dsh-demon 只读 | 只记录 hash，不写回 |
| 聊天记录 | 酒馆 | dsh-demon 增量索引 | 只追加，不复制原始文件 |
| 长期记忆 | dsh-demon | Demon 只读缓存 | 10 分钟过期 |
| 当前情绪 | Demon | dsh-demon 存档 | 变化时推送 |

## 聊天记录处理

- 扫描 `data/default-user/chats/**/*.jsonl`
- 记录 `size/mtime/line_count`，只读新增行
- 文件变小或行数回退 → 重建该文件索引
- 原文索引默认保留 30 天；记忆永久
- 云端摘要需显式开启，默认本地

## 契约

- `contracts/v1/events.schema.json`：WebSocket 事件与指令
- `contracts/v1/memory.schema.json`：记忆 append/query
- `contracts/v1/emotion.schema.json`：情绪状态
- 版本：`contracts/version.json`（1.0.0）

## 认证

- `dsh-demon` 监听 `127.0.0.1:8791`
- token 位于 `%LOCALAPPDATA%\dsh-demon\token`
- 请求头 `X-Dsh-Token`；WebSocket 用 `?token=`
