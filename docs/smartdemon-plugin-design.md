# smartdemon 酒馆插件设计

> 目标：在 SillyTavern 聊天界面里，播放 Demon 合成的语音，并且**可以点任意一句单独播放**。
> 定位：替代已下线的 `st-gptsovits5-voice`，但声线/权重全部交给 Demon 管理，插件只负责「选句 + 播放」。

---

## 1. 职责划分

| 层 | 负责 |
| --- | --- |
| 酒馆（浏览器） | 聊天界面、消息 DOM、点击交互、音频播放 |
| **smartdemon 插件** | 注入逐句按钮、分句、请求音频、播放队列、缓存、设置面板 |
| **Demon（Qt/C++）** | 声线档案、角色绑定、权重切换、调 GPT-SoVITS 合成、返回 WAV |

插件本身**不碰 GPT-SoVITS**，只跟 Demon 的 `8790` 说话。

```
用户点某一句
   │
   ▼
smartdemon (浏览器)
   │  POST http://127.0.0.1:8790/voice/speak
   │  { text, character, lang, speed }
   ▼
Demon ──► 角色绑定查声线 ──► 切权重 ──► api_v2(9880) ──► WAV
   │
   ▼
插件用 <audio> 播放这个 Blob
```

---

## 2. 功能清单

### 2.1 句子级播放（核心需求）

- AI 消息渲染后，把正文按句切成 `<span class="sd-sent" data-sd-i="0">`，**不破坏原有 HTML**（表情、代码块、引用保持原样）
- 鼠标悬停消息 → 每句右侧出现小喇叭
- 点第 3 句 → 只合成并播放第 3 句（不是整段）
- 再点第 5 句 → 立刻停掉第 3 句，播第 5 句

### 2.2 整段播放

- 消息底部一排控制：`▶ 整段` / `⏸ 暂停` / `🔁 重播`
- 整段 = 按句子顺序排队，逐句请求 + 逐句播放
- 播放中高亮当前句

### 2.3 角色声线

- 请求里带 `character`（角色卡名），Demon 按 `characterVoices` 选声线
- 没绑定的角色用 Demon 的默认声线
- 插件设置里可临时覆盖（比如"这条消息用 demon 声线试听"）

### 2.4 自动朗读

- 开关打开后，ST 的 `MESSAGE_RECEIVED` 事件触发整段播放
- 默认关闭（避免和 ST 内置 TTS 打架）

### 2.5 其它

- 语速 / 音量（传给 Demon 或本地 audio 音量）
- 长消息截断（默认 300 字，超出部分不朗读，提示）
- Demon 未启动时按钮置灰 + toast 提示
- 播放缓存（同一句不重复合成）

---

## 3. Demon 侧接口约定

### 3.1 已有

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/healthz` | 探活（插件启动时探测） |
| GET | `/voice/status` | 声线列表、默认声线、队列状态 |
| POST | `/voice/speak` | 合成并返回 `audio/wav` |

### 3.2 需要扩展 `/voice/speak`

请求体新增两个可选字段：

```json
{
  "text": "你好呀，今天过得怎么样？",
  "character": "小鲸鱼娘",
  "profile": "demon-小恶魔",
  "lang": "zh",
  "speed": 1.0
}
```

优先级：`profile` > `character` 绑定 > Demon 默认声线。

响应：

- 成功：`200` + `Content-Type: audio/wav` + WAV 字节
- 参数错：`400` + `{"error":{"message":"..."}}`
- 语音服务没起：`502` + 同上

### 3.3 可选新增（提升体验）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/voice/profile?character=小鲸鱼娘` | 返回该角色实际用的声线 id，插件用来显示"当前声线" |
| POST | `/voice/prewarm` | 预热（提前切好权重），减少首句延迟 |

---

## 4. 插件目录结构

```
smartdemon/
├─ manifest.json          { display_name, loading_order, js, css }
├─ index.js               入口：注册设置面板、消息钩子、按钮注入
├─ style.css              按钮/高亮样式
├─ src/
│  ├─ settings.js         读写 extension_settings.smartdemon
│  ├─ demon-client.js     fetch 封装（超时/重试/错误归一/探活）
│  ├─ split.js            分句（规则和 Demon 的 TextSplit 保持一致）
│  ├─ player.js           播放队列、打断、缓存、进度回调
│  └─ ui.js               句子 span 包裹、按钮注入、高亮
└─ README.md
```

---

## 5. 设置项（`extension_settings.smartdemon`）

```json
{
  "enabled": true,
  "endpoint": "http://127.0.0.1:8790",
  "autoPlay": false,
  "speed": 1.0,
  "volume": 1.0,
  "profileOverride": "",
  "maxChars": 300,
  "showSentenceButtons": true
}
```

---

## 6. 关键实现点

### 6.1 分句与 DOM 不破坏

- 只处理 `.mes:not(.is_user) .mes_text`
- 遍历文本节点，按 `。！？!?…\n` 切；遇到 `<code>`/`<pre>`/`<img>` 等元素直接跳过
- 每个句子包一层 `<span class="sd-sent" data-sd-i="n">`，**保留原节点引用**
- 消息被编辑/重新生成时，先移除旧 span（`unwrap`）再重新包裹

### 6.2 取句子文本

```js
const text = span.textContent.trim();
```

如果句子含表情占位（`*动作*`），发请求前去掉，避免让它念动作描写。

### 6.3 音频获取与缓存

```js
const key = `${profile}|${speed}|${text}`;
if (cache.has(key)) return cache.get(key);        // Blob URL
const res = await fetch(`${endpoint}/voice/speak`, {...});
const blob = await res.blob();
const url = URL.createObjectURL(blob);
```

- 缓存上限 50 条，超出按 LRU 释放（`URL.revokeObjectURL`）
- 请求超时 120 秒（首句要加载权重，可能 10 秒+）

### 6.4 播放队列与打断

```js
player.play(sentences)   // 入队
player.skipTo(index)     // 点某句：清空队列，只播这句
player.stop()            // 暂停并清空
```

- 同一时刻只有一个 `<audio>` 在响
- 播完一句自动下一句；出错跳到下一句并 toast

### 6.5 自动朗读

```js
eventSource.on(event_types.MESSAGE_RECEIVED, async (mesId) => {
  if (!settings.autoPlay) return;
  await waitForRender(mesId);       // 等 DOM 出来
  player.playMessage(mesId);
});
```

### 6.6 错误处理

| 情况 | 表现 |
| --- | --- |
| `fetch` 失败（Demon 没开） | 按钮置灰 + toast「Demon 未运行（8790）」 |
| `502`（语音服务没开） | toast「语音服务未启动，请先在 Demon 里启动」 |
| 单句合成失败 | 跳过该句，继续下一句 |

---

## 7. 与旧插件 `st-gptsovits5-voice` 的对比

| | 旧插件 | smartdemon |
| --- | --- | --- |
| 合成方 | 插件直接调 9880 | 插件调 Demon(8790)，Demon 调 9880 |
| 声线管理 | 插件设置里 | Demon 的 `voiceProfiles` + `characterVoices` |
| 权重切换 | 插件自己调 set_*_weights | Demon 负责，带缓存 |
| 播放粒度 | 整段 | **整段 + 逐句** |
| 依赖 | 直连 GPT-SoVITS | 只依赖 Demon |

---

## 8. 里程碑

| 阶段 | 内容 | 估时 |
| --- | --- | --- |
| M1 | 骨架 + 设置面板 + 整段播放（调 `/voice/speak`） | 4h |
| M2 | 逐句 span + 小喇叭 + 点击单句 + 打断 | 5h |
| M3 | 播放队列、高亮当前句、缓存、错误提示 | 3h |
| M4 | 自动朗读 + 角色声线显示 + 文档 | 3h |
| 合计 | | **约 15h（2 个工作日）** |

---

## 9. 验收清单

- [ ] 点第 N 句，只播第 N 句，不播整段
- [ ] 快速连点不同句子，声音不重叠
- [ ] 整段播放按顺序，能暂停/继续
- [ ] 角色 A、B 分别用不同声线（Demon 里已绑定）
- [ ] 关掉 Demon 后点播放，有明确提示而不是静默
- [ ] 刷新页面后插件设置还在
- [ ] 不破坏消息里的表情/代码块/引用

---

## 10. 待确认

1. 逐句按钮的交互：悬停显示 / 常驻小喇叭 / 点击消息后弹出菜单？（建议悬停显示）
2. 自动朗读默认关还是开？（建议默认关，避免和 ST 内置 TTS 冲突）
3. 是否需要"只读对话中角色说的话"（引号内）？（旧插件有这个 `readQuotedOnly` 选项，可作 v2）
