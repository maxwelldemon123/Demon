# -*- coding: utf-8 -*-
"""更新 DEVLOG / README（D5）。"""

import io

ROOT = r"E:\dshwork\Demon"

devlog = """
## 2026-10-24 · 1.0 D5 完成（稳定性 + 打包 + 真模型）

### 稳定性

| 场景 | 处理 | 实测 |
| --- | --- | --- |
| 上游中途断开 | 发 `data: {"error":...}` + `data: [DONE]`，客户端不会一直转圈 | 停掉假上游后 4.1s 返回错误事件 |
| 端口被占用 | 弹窗提示 + 日志，不再静默退出 | 代码路径（未在无头环境实测弹窗） |
| 首包失败 | 同上，带 `[DONE]` | 已验证 |

### 打包（dist\\Demon）

- `DEMON_CONSOLE=OFF` 构建 → 子系统 = Windows GUI（无控制台窗口），exe 155 KB
- windeployqt 后整包 **44.8 MB / 32 文件**（含 Qt6 + FFmpeg 多媒体运行库）
- 脚本：`启动Demon.bat` `停止Demon.bat` `安装开机启动.bat` `卸载开机启动.bat`
  - bat 必须 **GBK + CRLF**，UTF-8 会被 cmd 按字节拆成命令（踩过：`'ul' is not recognized`）
  - 开机自启只写 `HKCU\\...\\Run`，实测安装 → 注册表有值 → 卸载 → 已清除
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
"""

readme_patch_old = """
## 自测

```bat
python tools\\smoke_test.py
```

跑 12 项检查：接口、两条声线合成、流式、上游路由、队列排空。
"""

readme_patch_new = """
## 构建

```bat
:: 开发版（带控制台，方便看日志）
tools\\build.bat

:: 发布版（无控制台）
cmake -S . -B build-release -G Ninja -DCMAKE_BUILD_TYPE=Release -DDEMON_CONSOLE=OFF ^
      -DCMAKE_PREFIX_PATH=E:\\dshwork\\toolchain\\Qt\\6.8.3\\msvc2022_64
cmake --build build-release
```

## 发布包（dist\\Demon）

```
dist\\Demon\\
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
python tools\\smoke_test.py          :: 12 项接口/语音/路由检查
python tools\\real_model_test.py 4   :: 多轮真模型对话（需先配好 upstream）
```
"""

log = io.open(f"{ROOT}\\docs\\DEVLOG.md", encoding="utf-8").read()
if "D5 完成" not in log:
    io.open(f"{ROOT}\\docs\\DEVLOG.md", "a", encoding="utf-8", newline="").write(devlog)

readme = io.open(f"{ROOT}\\README.md", encoding="utf-8").read()
if readme_patch_old in readme:
    readme = readme.replace(readme_patch_old, readme_patch_new)
else:
    print("[warn] README 锚点未命中，追加到末尾")
    readme += readme_patch_new
io.open(f"{ROOT}\\README.md", "w", encoding="utf-8", newline="").write(readme)

print("docs updated")
