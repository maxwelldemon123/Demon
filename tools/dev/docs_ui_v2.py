# -*- coding: utf-8 -*-
"""更新文档：新 UI 导航、启动器、角色声线。"""

import io

DIST = r"E:\dshwork\Demon\dist\Demon"
ROOT = r"E:\dshwork\Demon"

p = f"{DIST}\\使用说明.txt"
txt = io.open(p, encoding="utf-8-sig").read()

start = txt.index("二、启动")
end = txt.index("三、让酒馆连上")
new_block = """二、启动
--------
双击桌面 Demon 快捷方式（或 启动Demon.bat），出现主窗口。
左侧是导航，右侧是面板：

  状态   接口地址 / 上游 / 默认声线 / 队列，以及复制地址、打开日志等
  接口   上游列表（ID、地址、模型、密钥）和默认上游；改完点「保存并生效」
  启动   一键启动/停止 SillyTavern 与 GPT-SoVITS（路径已预填，可改）
  语音   4 条声线档案：ID / 名称 / 参考音频 / GPT 权重 / SoVITS 权重 / 提示文本
         可添加、删除、保存、试听、设为默认
  角色   读取酒馆角色卡目录，给每个角色指定声线；聊到该角色自动切换
  日志   实时看 demon.log

关窗口 = 退出程序。开机自启用「安装开机启动.bat」。

"""
txt = txt[:start] + new_block + txt[end:]

# 在“五、语音”后面补角色绑定说明
if "角色声线（自动切换）" not in txt:
    marker = "六、开机自启（可选）"
    add = """五之二、角色声线（自动切换）
------------------------------
在「角色」页给角色卡指定声线后，聊天时 Demon 会在请求文本里识别角色名，
自动切到对应声线；没指定的角色用默认声线。

注意：识别方式是“请求里出现角色名”，所以角色卡名字要和酒馆里一致。

"""
    txt = txt.replace(marker, add + marker)

io.open(p, "w", encoding="utf-8", newline="").write(txt)
print("[OK] 使用说明")

devlog = """
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
- 酒馆：`<stPath>\\Start.bat`
- 语音：`<gsvPath>\\start-api-v2pro.bat`
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
"""
log = io.open(f"{ROOT}\\docs\\DEVLOG.md", encoding="utf-8").read()
if "UI 重构（仿 Electron 版）" not in log:
    io.open(f"{ROOT}\\docs\\DEVLOG.md", "a", encoding="utf-8", newline="").write(devlog)
    print("[OK] DEVLOG")
