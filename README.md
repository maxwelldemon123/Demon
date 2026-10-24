# Demon

本地桌面伴侣的**引擎**：对外提供 OpenAI 兼容的 HTTP 端点，让酒馆（SillyTavern）当界面，Demon 负责模型路由、语音（规划中）、Live2D（2.0）与硬件（3.0）。

> 路线图与设计决策见 `E:\dshwork\plan-doc\Demon-技术方案与实施计划书-v1.3.docx`
> 开发日志见 `docs/DEVLOG.md`

## 当前能力（1.0 D1+D2）

| 端点 | 说明 |
| --- | --- |
| `GET /healthz` | 健康检查：版本、运行时长、上游、语音配置 |
| `GET /v1/models` | 模型列表（酒馆用它填下拉框） |
| `POST /v1/chat/completions` | `stream=true` 时 SSE 透传到上游，结束后自动朗读 |
| `GET /voice/status` | 声线、队列、busy、自动朗读开关 |
| `POST /voice/speak` | 单句合成，返回 `audio/wav` |
| `OPTIONS *` | CORS 预检；流式期间每 15s 发 `:keep-alive` |

## 托盘菜单

- **声线**：xiaod / demon 单选（写回 `config.json`）
- **自动朗读**：开 / 关（写回 `config.json`）
- 打开日志 / 打开配置目录 / 重载配置 / 退出

## 构建

```bat
:: 开发版（带控制台，方便看日志）
tools\build.bat

:: 发布版（无控制台）
cmake -S . -B build-release -G Ninja -DCMAKE_BUILD_TYPE=Release -DDEMON_CONSOLE=OFF ^
      -DCMAKE_PREFIX_PATH=E:\dshwork\toolchain\Qt\6.8.3\msvc2022_64
cmake --build build-release
```

## 发布包（dist\Demon）

```
dist\Demon\
├─ demon.exe            无控制台窗口
├─ Qt6*.dll + 插件       windeployqt 生成
├─ config.json           配置
├─ 启动Demon.bat / 停止Demon.bat
├─ 安装开机启动.bat / 卸载开机启动.bat   （只写 HKCU）
└─ 使用说明.txt
```

整包约 45 MB，绿色免安装。

## 自测

```bat
python tools\smoke_test.py          :: 12 项接口/语音/路由检查
python tools\real_model_test.py 4   :: 多轮真模型对话（需先配好 upstream）
```

## 快速开始

### 1. 构建

```bat
tools\build.bat
```

依赖（本机已装好）：
- Visual Studio 2022（MSVC 14.44）
- Qt 6.8.3 msvc2022_64（`E:\dshwork\toolchain\Qt\6.8.3\msvc2022_64`）
- CMake / Ninja（VS 自带）

### 2. 配置

首次运行会在 `build\bin\config.json` 生成配置。示例：

```json
{
  "listen": { "host": "127.0.0.1", "port": 8790 },
  "modelId": "demon",
  "upstreams": [
    { "id": "local", "baseUrl": "http://127.0.0.1:8080/v1", "model": "qwen", "apiKey": "" },
    { "id": "cloud", "baseUrl": "https://api.example.com/v1", "model": "chat", "apiKey": "sk-..." }
  ],
  "defaultUpstream": "local",
  "voice": { "endpoint": "http://127.0.0.1:9880", "profile": "xiaod", "autoPlay": true, "speed": 1.0 }
}
```

### 3. 启动

```bat
build\bin\demon.exe
```

托盘出现 D 图标；右键可看日志、打开配置目录、重载配置、退出。

### 4. 让酒馆连上

酒馆 → **Chat Completion** → Chat Completion Source 选 **Custom (OpenAI-compatible)**：

```
Custom Endpoint : http://127.0.0.1:8790/v1
Custom API Key  : （留空或随便填）
Model           : demon
```

发一条消息，应该能看到流式输出。

## 本地联调（不接真实模型）

```bat
:: 假上游：模拟 OpenAI 流式接口
python tools\fake_upstream.py

:: 把 config.json 的 upstream 指过去
{ "id": "fake", "baseUrl": "http://127.0.0.1:8899/v1", "model": "fake-model" }
```

## 目录

```
Demon/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   ├── app/AppController.*    路由、托盘、流式转发
│   ├── http/HttpServer.*      极简 HTTP/1.1 服务器
│   ├── config/Config.*        config.json
│   └── util/Log.*             控制台 + 文件日志
├── tools/
│   ├── build.bat              一键构建
│   └── fake_upstream.py       假上游
├── docs/DEVLOG.md
└── build/                     构建产物（含配置与日志）
```

## 许可

私有项目，暂未选择开源许可。
