# Demon — 开发日志

## 2026-10-24 · 1.0 D1 + D2 完成

### 目标
按 v1.3 计划书的主方向（反向集成）落地：Demon 对外提供 OpenAI 兼容端点，酒馆当界面。

### 已完成

| 项 | 状态 |
| --- | --- |
| 仓库骨架（CMake + Qt 6.8.3 + MSVC 2022） | ✅ |
| 极简 HTTP/1.1 服务器（QTcpServer，自解析） | ✅ |
| `GET /healthz` | ✅ |
| `GET /v1/models` | ✅ |
| `OPTIONS` 预检 + CORS（回显 Origin） | ✅ |
| `POST /v1/chat/completions` SSE 流式透传 | ✅ |
| 托盘图标 + 菜单（日志/配置目录/重载/退出） | ✅ |
| 日志落盘（`bin/data/demon.log`） | ✅ |
| 配置文件自动生成（`bin/config.json`） | ✅ |
| 假上游（`tools/fake_upstream.py`）用于本地验证 | ✅ |

### 实测证据

```
GET /healthz        → 200，返回 model/upstream/voice
GET /v1/models      → 200，data[0].id = demon
OPTIONS             → 204，ACAO 回显
POST stream=true    → 200 text/event-stream，17 个 data 事件，末行 data: [DONE]
                      首包 6 ms 到达（未缓冲），总耗时 1.98s（上游每 token 120ms）
POST stream=false   → 501（非流式留到后续）
```

### 踩到的坑与修复

1. **流式回调悬空指针导致 0xC0000005 崩溃**
   - 原因：`HttpStream` 是 `onReadyRead` 里的栈对象，异步回调按引用捕获。
   - 修复：`HttpStream` 改为 `shared_ptr`，由 `HttpServer::Client` 持有；socket 用 `QPointer` 防悬空；转发逻辑抽成独立 `StreamJob`（parent = reply，随 reply 销毁）。

2. **`writeHead` 被重构误删**
   - 现象：curl 收到的是裸 `data: ...`，没有 HTTP 头。
   - 修复：在 `post()` 之前显式 `stream->writeHead(200, "text/event-stream")`。

3. **`unique_ptr` 与 QObject parent 双重持有**
   - `QNetworkAccessManager` / `HttpServer` 既被 `unique_ptr` 管理，又传了 `this` 作 parent → 退出时双重删除。
   - 修复：不给 parent，统一由 `unique_ptr` 管理。

### 已知限制（D3 处理）

- 非流式请求返回 501（酒馆默认流式，可接受）。
- 没有 SSE 保活（`KeepAliveSeconds` 配置项已预留，未实现）。
- 上游只支持一个默认；按 model 名分流未实现。
- TTS 未接入（D3）。

### 如何复现验证

```bat
:: 1. 启动假上游
"<python.exe>" tools\fake_upstream.py

:: 2. 构建并启动
tools\build.bat
build\bin\demon.exe

:: 3. 测试
curl -N -X POST http://127.0.0.1:8790/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  --data-binary "@build\req.json"
```

## 2026-10-24 · 1.0 D3 完成（语音）

### 已完成

| 项 | 说明 |
| --- | --- |
| `TtsClient` | 调 GPT-SoVITS api_v2 的 `/tts`，返回 WAV |
| `AudioPlayer` | QMediaPlayer + QAudioBuffer，内存播放，无需落盘 |
| 分句 | `splitForSpeech()`：按句末标点切，过长再按逗号切，去掉 *动作* 与（动作） |
| 语种判定 | 假名→ja / 汉字→zh / 韩文→ko / 其余 en |
| 语音队列 | 逐句合成 → 播放 → 下一句（按 WAV 时长估算间隔） |
| 自动朗读 | 每条回复流式结束后自动触发（配置 `voice.autoPlay`） |
| `GET /voice/status` | 端点、声线、队列、busy、可用档案 |
| `POST /voice/speak` | 单句合成，直接返回 `audio/wav`（便于命令行验证） |
| 两条声线 | xiaod / demon，参考音频与 prompt 写在 config.json |

### 实测

```
POST /voice/speak  {"text":"主人，晚上好。","profile":"xiaod","lang":"zh"}
  → HTTP 200, 152,364 字节, RIFF/WAVE, 8.8s（含模型首次加载）

酒馆里发一条消息（回复 20 字）：
  回调：收到完整文本 20 字
  准备朗读 2 句
  合成[zh]：你好，我是Demon。      → 133 KB → 开始播放
  合成[zh]：这是一次流式测试。      → 186 KB → 开始播放
  单句合成耗时 1.1~1.5s（热态）
```

### 本阶段修掉的 bug

1. `accumulate()` 没被调用（补丁没命中）→ 文本一直是 0 字。
2. `StreamJob` 构造函数漏了 `m_onText` 初始化 → 完成回调永远不触发。
3. 老 `config.json` 没有 `voiceProfiles` → 启动时档案为 0；现在缺省补两条。
4. `/voice/speak` 先发 200 再合成失败，把错误文本写进了 wav；改成合成完成后再发头（失败 502）。

### 已知限制

- 声线只能改配置，托盘还没有切换菜单（D4）。
- 没有按角色自动选声线。
- 首句延迟 = 合成时间（1~8s），尚未做"边写边合成"。
- 播放设备用系统默认。
## 2026-10-24 · 1.0 D4 完成（托盘 + 保活 + 路由 + 音量）

### 新增

| 项 | 说明 | 验证 |
| --- | --- | --- |
| 托盘「声线」子菜单 | xiaod / demon 单选，切换即写回 config.json | 代码路径 + 配置持久化 |
| 托盘「自动朗读」开关 | 勾选状态写回 config.json | 同上 |
| SSE 保活 | 每 `keepAliveSeconds` 秒发 `:keep-alive` | **实测**：慢上游沉默 6s，收到 2 条保活 |
| 上游按模型名路由 | 请求 model 匹配上游 id/model 时定向，否则回落默认 | **实测**：fake-model-b 打到 8898，demon/nope 打到 8899 |
| 音量 | `voice.volume` → QAudioOutput | 编译通过，待听感确认 |

### 自动化冒烟测试（`tools/smoke_test.py`）

```
== 1. 基础接口 ==      healthz / models / voice/status        ✓ ✓ ✓
== 2. 语音合成 ==      xiaod 中文 4.76s / demon 日文 3.72s / 空文本 400   ✓ ✓ ✓
== 3. 流式对话 ==      17 个事件, [DONE], text/event-stream    ✓ ✓
== 4. 上游路由 ==      fake-model → 8899, fake-model-b → 8898, 未知 → 回落   ✓ ✓ ✓
== 5. 语音队列 ==      最终排空                                ✓
通过 12/12
```

### 备注

- 语音合成热态 1.3~1.4s/句（32 kHz WAV）。
- 慢上游测试暴露一个正常行为：客户端（curl 管道被提前关闭）断开时会中止上游，日志会记 `WARN 客户端提前断开`，这是预期。
## 2026-10-24 · 1.0 D5 完成（稳定性 + 打包 + 真模型）

### 稳定性

| 场景 | 处理 | 实测 |
| --- | --- | --- |
| 上游中途断开 | 发 `data: {"error":...}` + `data: [DONE]`，客户端不会一直转圈 | 停掉假上游后 4.1s 返回错误事件 |
| 端口被占用 | 弹窗提示 + 日志，不再静默退出 | 代码路径（未在无头环境实测弹窗） |
| 首包失败 | 同上，带 `[DONE]` | 已验证 |

### 打包（dist\Demon）

- `DEMON_CONSOLE=OFF` 构建 → 子系统 = Windows GUI（无控制台窗口），exe 155 KB
- windeployqt 后整包 **44.8 MB / 32 文件**（含 Qt6 + FFmpeg 多媒体运行库）
- 脚本：`启动Demon.bat` `停止Demon.bat` `安装开机启动.bat` `卸载开机启动.bat`
  - bat 必须 **GBK + CRLF**，UTF-8 会被 cmd 按字节拆成命令（踩过：`'ul' is not recognized`）
  - 开机自启只写 `HKCU\...\Run`，实测安装 → 注册表有值 → 卸载 → 已清除
- `使用说明.txt`：酒馆配置、配置项、排错

### 真模型联调

本机 DSH 网关 `127.0.0.1:8099` 提供 `local-vl`（Qwen3-VL-4B）：

```
4 轮对话：0.6s / 0.1s / 0.1s / 0.1s（模型已在内存）
内存：36.2 MB → 36.2 MB（无增长）
每轮都触发 TTS 并播放（93~466 KB WAV）
```

注意：该网关会用「视觉子代理」系统提示词覆盖，所以回复风格不是聊天模型；
换真聊天模型只需改 `upstreams` 的 baseUrl/model。

### 已知限制

- 端口冲突弹窗在无桌面会话下会阻塞（正常桌面无影响）
- 没有单实例检测（重复启动会弹窗后退出，可接受）
- `dist` 里的 config 指向 8099（本机 DSH 网关），换机器要改

### 环境核查（D5 收尾）

- 本次安装/构建全部落在 E 盘：Qt、构建产物、dist、测试数据。
- 本会话临时文件已清理 64 MB（`%TEMP%\dsh-subprocess-*`、ego 截图）。
- C 盘从 24.1 GB → 18.6 GB 的主要原因是 **系统页面文件**（`C:\pagefile.sys` 当前分配 12.3 GB，峰值仅 1.5 GB）
  以及既有的 VS 安装缓存（2.6 GB）和 gopeed 预取文件（1 GB，10-22 生成，非本项目）。
  项目本身没有向 C 盘写入任何文件。
## 2026-10-24 · 控制窗口（解决“找不到托盘图标”）

### 背景
用户反馈看不到托盘内容。排查结论：进程与 explorer 同会话（Session 2），
托盘创建成功（日志 `系统托盘可用=是`），但 **Windows 11 把新图标默认放进折叠区**，
注册表 `NotifyIconSettings` 里也没有登记项。

### 改动
1. 新增 `ControlWindow`（Qt Widgets）：运行状态 / 声线切换 / 自动朗读开关 /
   复制接口地址 / 打开日志 / 配置目录 / 重载配置 / 退出。
2. 启动即显示控制窗口，托盘图标保留为快捷方式（双击重新打开窗口）。
3. 启动气泡提示：“右键托盘 D 图标…如果没看到，点任务栏 ^”。
4. 单实例检测（QSharedMemory）：重复双击不再弹“端口被占用”，
   而是提示“已经在运行”。
5. 端口占用文案补充“最常见原因是已经有一个 Demon 在运行”。

### 踩坑
- 无 DPI 感知的 PowerShell 里 `GetWindowRect` 返回的是**虚拟化坐标**（1.75 倍缩放），
  截出来的窗口总像被裁掉。用 `SetProcessDpiAwarenessContext(-4)` 后拿到真实尺寸
  （1214x624，屏幕 2560x1440），确认窗口完整。
- 窗口尺寸不能写死：固定 560 宽会裁掉按钮；最终用
  `layout()->setSizeConstraint(QLayout::SetMinimumSize)` 让布局决定最小尺寸。

## 2026-10-24 · 托盘图标问题定论

### 现象
- 用户看不到 Demon 托盘图标；Win11「其他系统托盘图标」列表里也没有 Demon。
- 程序侧日志：`isSystemTrayAvailable=是`、`isVisible=1`、`iconNull=0`，
  但 `geometry=0x0`。

### 对照实验
1. 写了一个 20 行最小 Qt 托盘程序（红色圆点）：
   `available=true visible=true geometry=0x0`，注册表 `NotifyIconSettings` 同样无记录。
2. 重启 Explorer 后重试：仍然无位置、无登记。

### 结论
**不是 Demon 的代码问题，是这台 Win11 不注册新的第三方托盘图标。**
（`HKCU\Control Panel\NotifyIconSettings` 里只有 Quark/WeGame/OneDrive 等既有条目，
新程序不会生成条目，因此也不会出现在设置页。）

### 应对
- 控制窗口作为主界面，启动即显示。
- 关闭窗口 = 退出程序（避免“看不见也关不掉”）。
- 托盘仍保留（万一以后系统恢复了能用），但不再作为唯一入口。
- 文档里说明：想快速启动就建桌面快捷方式或固定到任务栏。

## 2026-10-24 · 音色档案从酒馆插件迁入 Demon

### 背景
用户要求：`st-gptsovits5-voice` 插件只保留音色档案并留存在 Demon，酒馆端删掉插件。

### 档案来源
插件配置存在酒馆 `settings.json` 的 `extension_settings.gptsovits5_voice`，
共 4 条档案（id / gptWeights / sovitsWeights / refAudio / promptText / promptLang）。

### 迁移动作
1. `VoiceProfileConfig` 增加 `name` / `gptWeights` / `sovitsWeights`。
2. `TtsClient::ensureWeights()`：合成前比对当前权重，不同则依次 GET
   `/set_gpt_weights?weights_path=...`、`/set_sovits_weights?weights_path=...`，
   成功后才合成；`/voice/speak` 与自动朗读都走这条路径。
3. 参考音频复制到 `dist\Demon\voices\`，配置里用绝对路径（api_v2 的相对路径按它自己的 cwd 解析）。
4. 4 条档案写入 `config.json`，默认声线 `小d-柔软`。

### 酒馆端清理
- 检查 `public/scripts/extensions/third-party`、`plugins/`：**插件代码本来就不在了**。
- 删除 `settings.json` 里的 `gptsovits5_voice` 配置（先备份到
  `E:\dshwork\st-gptsovits5-voice\_st-backup\`）。
- 注意：酒馆当时正在运行（pid 20104），它下次保存设置时可能用内存里的旧配置覆盖；
  重启一次酒馆即可固定，或运行 `dist\Demon\清理酒馆插件残留.bat`。

### 实测
```
小d-柔软       -> 200  157 KB  3.5s
demon-小恶魔   -> 200  178 KB  3.2s
小d-柔软-泛化  -> 200  175 KB  2.7s
demon-小恶魔-2 -> 200  181 KB  2.7s
日志：权重已切换：...（每条切换 0.3~0.5 秒）
自检：5/5 PASS（profiles 显示 4 条）
```

## 2026-10-24 · UI 重构（仿 Electron 版）+ 启动器 + 角色声线

### 新界面
左侧深色导航（状态/接口/启动/语音/角色/日志），右侧 QStackedWidget 面板，
整体仿 1.0 Electron 版的三栏观感（不含聊天界面）。

- 状态：接口地址、上游、模型、默认声线、队列 + 快捷按钮
- 接口：上游表格（可增删改）+ 默认上游，保存后热加载
- 启动：SillyTavern 与 GPT-SoVITS 路径（已预填）、端口、启动/停止/打开页面
- 语音：4 条档案表格 + 试听 / 设为默认
- 角色：扫描 `characters` 目录，逐角色绑定声线
- 日志：日志尾部查看

### 启动器实现
`QProcess::startDetached("cmd.exe", {"/c","start","",bat}, workdir)`：
- 酒馆：`<stPath>\Start.bat`
- 语音：`<gsvPath>\start-api-v2pro.bat`
停止：解析 `netstat -ano -p tcp` 找端口对应 pid，再 `taskkill /PID /F`。
状态：每 1.5 秒探测 8000 / 9880 端口，绿点=运行中。

### 角色声线
`config.characterVoices`（角色名 → 档案 id）。
请求到达时 `detectCharacterProfile()` 在请求体里找绑定的角色名（取最长匹配），
写入 `m_pendingProfile`，朗读时优先使用；没有匹配则用默认声线。

### 实测
```
请求 system 里含「小鲸鱼娘」：
  识别到角色 小鲸鱼娘，使用声线 demon-小恶魔
  准备朗读 1 句（声线 demon-小恶魔）
  权重已切换：GPT_weights_v2Pro/nightmare-JP-e15.ckpt
  权重已切换：SoVITS_weights_v2Pro/nightmare-JP_e8_s368.pth
  TTS 合成完成：2 字 / 68 KB
```

### 踩坑
- 截图看起来“页面错位”，实际是 PrintWindow 抓到切换前的旧帧；
  用 UIA 的 BoundingRectangle 定位点击 + 等待 900ms 后正常。
- PowerShell 单引号字符串里的 `` `r`n `` 是字面量，会写进 C++ 源码导致编译失败（又踩一次）。

## 2026-10-24 · 启动酒馆后自动打开浏览器

### 实现
点「启动酒馆」后：
1. 调 Start.bat 拉起酒馆；
2. 每 600ms 探测一次端口，最多等 72 秒；
3. 端口一通就打开 http://127.0.0.1:<端口>/；
4. 若酒馆本来就在跑，直接打开页面。
「打开页面」按钮也走同一函数。

打开方式按顺序尝试：默认浏览器 exe（从注册表读）→ cmd start → rundll32 → QDesktopServices。

### 没能当场验证的原因
当前调试环境会拦截 GUI 子进程：
- 从 Demon 里 CreateProcess 启动 notepad / msedge，返回成功但进程秒退；
- 连 pwsh 的 Start-Process 启 GUI 程序都报 "The operation was canceled by the user"；
- 控制台子进程（node/cmd）正常（酒馆就是被 Demon 启动并一直跑着）。

结论：这是**沙箱限制 GUI 子进程**，不是代码问题。用户双击桌面快捷方式的正常会话不受此限制。

## 2026-10-24 · smartdemon 插件（改造版）

### 做法
不重写，直接把 `st-gptsovits5-voice` 改造成 `plugin/smartdemon`：
保留 UI/分句/队列/绑定逻辑（约 70%），只换后端。

| 文件 | 处理 |
| --- | --- |
| lib/tts-text.js | 保留；cacheKey 改用 profile.id；normalizeProfile 放宽（权重归 Demon） |
| style.css | 保留，新增选句菜单样式 |
| index.js | 换网络层：9880 → 8790；删 setWeights；档案表单只读；新增选句菜单 |
| server/ | 删除（Demon 处理 CORS） |

### 新增能力：逐句播放
每条 AI 消息两个按钮：
- 🔊 耳机：整条朗读（Shift=换声线，Alt=标注）
- ☰ 列表：弹出该消息的句子列表，点第 N 句只播第 N 句

### 实测（酒馆 1.18 + Demon）
```
插件加载 → 自动同步 4 条声线（小d-柔软 / demon-小恶魔 / 小d-柔软-泛化 / demon-小恶魔-2）
点耳机     → OPTIONS /voice/speak 204 → 切权重 → TTS 合成完成 14 字 / 293 KB
点列表→第1句 → /voice/speak → TTS 合成完成 23 字 / 332 KB
```

### 过程中修的三个问题
1. 历史消息没有按钮：init 时聊天 DOM 未渲染完 → 加 800ms/1800ms 延迟补装饰。
2. 未绑定角色直接报错：改为回退 Demon 默认声线。
3. 用户消息/系统提示也有按钮：按 is_user / smallSysMes 过滤。

### 环境处理
发现 `demon.exe` 被打上 `RUNASADMIN` 兼容性标记（导致每次弹 UAC、非管理员无法启动），
已从 `HKCU\...\AppCompatFlags\Layers` 清除；现在非管理员可正常启动。
