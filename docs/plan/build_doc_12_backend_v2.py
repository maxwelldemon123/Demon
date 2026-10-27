# -*- coding: utf-8 -*-
"""Demon 1.2 前后端数据结构与后端实现说明（UI 重构后版本）。"""

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

OUT = r"E:\dshwork\plan-doc\Demon-1.2-前后端数据结构与实现说明.docx"

doc = Document()
style = doc.styles["Normal"]
style.font.name = "微软雅黑"
style.font.size = Pt(10.5)
style.element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
for level in range(1, 4):
    h = doc.styles[f"Heading {level}"]
    h.font.name = "微软雅黑"
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    h.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)


def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, text in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(text)
        run.bold = True
        run.font.size = Pt(9.5)
    for row in rows:
        cells = t.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(text))
            run.font.size = Pt(9)
    if widths:
        for i, w in enumerate(widths):
            for r in t.rows:
                r.cells[i].width = Cm(w)


def code(text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)


title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("Demon 1.2 前后端数据结构与后端实现说明")
run.font.size = Pt(22)
run.bold = True
run.font.color.rgb = RGBColor(0x2B, 0x2B, 0x4A)

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.add_run("2026-10-26 · 对应 1.2 开发版（配置/角色/语音页重构后）").font.size = Pt(9.5)

doc.add_heading("1. 总体结构", level=1)
doc.add_paragraph(
    "Demon 是单进程 Qt Widgets 应用。主线程运行 UI 与 HTTP 服务，网络请求使用 QNetworkAccessManager 异步回调，"
    "没有独立工作线程。UI 只依赖 AppController 的公开方法与 uiDirty 信号。"
)
table(
    ["层", "组件", "职责"],
    [
        ["UI", "MainWindow（5 页）", "配置 / 启动 / 语音 / 角色 / Live2D；不再有日志页"],
        ["控制", "AppController", "路由、语音编排、Live2D 编排、启动器、配置与角色绑定"],
        ["HTTP 服务", "HttpServer", "手写 QTcpServer + HTTP/1.1 + SSE 流"],
        ["语音", "TtsClient / AudioPlayer / LipSync", "GPT-SoVITS、Qwen/CosyVoice、试听播放、口型包络"],
        ["Live2D", "VtsClient", "VTS WebSocket：认证、参数、表情、模型加载、窗口去边框"],
        ["配置", "Config", "JSON 持久化，全部默认值"],
    ],
    widths=[2.2, 5.8, 7.5],
)

doc.add_heading("2. 配置结构（config.json）", level=1)
code('''{
  "listen": { "host": "127.0.0.1", "port": 8790 },
  "modelId": "demon",
  "defaultUpstream": "local",
  "upstreams": [ { "id", "baseUrl", "model", "apiKey" } ],
  "voice": {
    "provider": "qwen", "endpoint": "http://127.0.0.1:9880",
    "profile": "小d-云端", "speed": 1.0, "volume": 1.0,
    "outputDevice": "", "translateToJa": false,
    "qwen": { "baseUrl": "...", "apiKey": "...", "model": "cosyvoice-v3.5-flash",
              "voice": "", "format": "wav", "sampleRate": 24000 }
  },
  "voiceProfiles": [
    { "id", "name", "refAudio", "promptText", "promptLang",
      "qwenVoice", "source": "local|cloud" }
  ],
  "characterVoices":    { "角色": "声线 id" },
  "characterProviders": { "角色": "local|cloud" },
  "characterModels":    { "角色": "Live2D 模型名" },
  "emotionHotkeys":     { "happy": "VTS 热键 ID" },
  "live2d": { "host", "port", "vtsExe", "modelsDir" },
  "launcher": { "stPath", "stPort", "gsvPath" }
}''')
table(
    ["字段", "新增/变化", "用途"],
    [
        ["voiceProfiles[].source", "1.2 新增", "local = GPT-SoVITS；cloud = 复刻音色"],
        ["voiceProfiles[].qwenVoice", "1.2 已有", "CosyVoice/Qwen 复刻音色 ID"],
        ["characterProviders", "1.2 新增", "角色级「本地音色 / 云端音色」开关"],
        ["characterModels", "1.2 新增", "角色绑定的 Live2D 模型"],
    ],
    widths=[5.0, 3.0, 7.0],
)

doc.add_heading("3. HTTP 接口", level=1)
table(
    ["方法", "路径", "说明"],
    [
        ["GET", "/healthz", "版本 / 上游 / 语音概要"],
        ["POST", "/v1/chat/completions", "SSE 透传上游"],
        ["POST", "/voice/speak", "{text, profile, lang, speed?, emotion?} → audio/wav"],
        ["GET", "/voice/status", "provider、模型、声线档案"],
        ["GET", "/live2d/status", "VTS 连接状态"],
        ["POST", "/live2d/emotion", "{emotion} → 表情"],
        ["POST", "/live2d/test", "{param,value} → 注入 MouthOpen"],
        ["GET", "/live2d/expressions", "当前模型表情表"],
        ["POST", "/live2d/raw", "调试：任意 VTS 请求"],
    ],
    widths=[1.8, 6.0, 8.0],
)

doc.add_heading("4. 页面与后端调用", level=1)
table(
    ["页面", "控件", "后端调用"],
    [
        ["配置", "上游表格 / 默认上游 / 保存", "saveApiTable → saveConfig + reloadConfig"],
        ["配置", "复制地址 / 打开日志 / 配置目录 / 重载", "openLogFile / openConfigFolder / reloadConfig"],
        ["启动", "酒馆、本地语音服务、云端语音服务、VTS", "startSillyTavern / startVoiceService / startVTubeStudio 等"],
        ["角色", "角色列表", "listCharacters()（读 ST characters 目录）"],
        ["角色", "本地/云端切换", "setCharacterProvider(character, source)"],
        ["角色", "声线 + / 试听 / 删除 / 选用", "voiceProfiles 编辑 + setCharacterVoice"],
        ["角色", "Live2D 绑定 / 加载", "setCharacterModel + loadLive2dModel"],
        ["语音-对接酒馆", "翻译开关 / 绑定表", "voice.translateToJa + setCharacterVoice"],
        ["语音-本地", "地址 / 语速 / 试听", "voice.endpoint / voice.speed / testVoice"],
        ["语音-云端", "模型 / API Key / 试听", "voice.qwen.* + testVoice"],
        ["Live2D", "重连 / 口型 / 情绪 / 独立显示", "reconnect / injectMouth / testEmotion / setVtsWindowBorderless"],
    ],
    widths=[3.0, 6.0, 7.0],
)

doc.add_heading("5. 语音链路", level=1)
doc.add_paragraph(
    "合成统一走 /voice/speak：按 profile 找到档案，provider=qwen 时请求 DashScope SpeechSynthesizer，"
    "model 由配置决定（cosyvoice-v3.5-flash 或 qwen-audio-3.1-tts-flash），voice 优先用 profile.qwenVoice。"
    "非流式响应是一个 24 小时有效的音频 URL，Demon 再下载为 WAV 返回。"
)
doc.add_paragraph(
    "中文→日语翻译位于 smartdemon 插件：输出语言非 auto 且与文本语言不同时，调用酒馆 generateQuietPrompt 翻译，"
    "再请求 /voice/speak。Demon 侧另有 translateToJa 兜底，默认关闭。"
)
doc.add_paragraph(
    "播放：酒馆页面由插件用 <audio> 播放；Demon 的 AudioPlayer 仅用于「试听」，输出设备跟随系统默认或手动选择。"
)

doc.add_heading("6. Live2D 链路", level=1)
table(
    ["阶段", "实现"],
    [
        ["连接", "ws://127.0.0.1:8001；token 存 data/vts-token.json；重连上限 12 次"],
        ["模型识别", "CurrentModelResponse 的 modelID → 匹配 .vtube.json → 定位模型目录"],
        ["表情表", "model3.json 的 Expressions；没有则递归扫 *.exp3.json（DS鲸鱼娘 属于这种）"],
        ["表情激活", "ExpressionActivationRequest + expressionFile + active；可叠加"],
        ["表情清除", "切情绪先 active:false 旧表情；8 秒无新情绪自动清空；水印常驻"],
        ["口型", "LipSync 解析 PCM16 WAV → 30fps RMS 包络 → InjectParameterData(MouthOpen)"],
        ["模型加载", "AvailableModelsRequest → 按 modelName 找 modelID → ModelLoadRequest"],
        ["独立显示", "Win32 去掉 VTS 窗口边框 + 置顶（背景透明需在 VTS 内设置）"],
        ["动作映射", "HotkeysInCurrentModelRequest 列热键 → emotionHotkeys 保存 → HotkeyTriggerRequest 触发"],
        ["桌宠模式", "WS_EX_LAYERED + LWA_COLORKEY 色键透明 + 置顶 + 隐藏任务栏"],
    ],
    widths=[3.0, 12.5],
)

doc.add_heading("7. 酒馆侧（1.2 同时调整）", level=1)
table(
    ["项", "状态"],
    [
        ["插件顶部耳机图标", "已移除；文段内耳机按钮保留"],
        ["插件面板", "仍构建但隐藏，配置改到 Demon 语音页"],
        ["Shift+点击耳机", "切换到该角色的下一条声线"],
        ["STMemoryBooks", "自动总结开启（每 50 条）"],
        ["内置 Memory", "source 改为 main（用当前聊天模型摘要，无需 Extras）"],
        ["世界书", "32 条，统一 [001]–[032] 编号，追加 3 条新剧情"],
        ["角色卡", "PNG 内嵌 description 追加「近期经历（1.2）」"],
    ],
    widths=[5.5, 10.0],
)

doc.add_heading("8. 已知问题与优化方向", level=1)
table(
    ["问题", "影响", "建议"],
    [
        ["AppController 仍然偏大", "继续加功能会难维护", "拆 VoiceService / LauncherService / Live2dService"],
        ["UI 直接改 m_config", "多处 saveConfig，易漏字段", "统一 SettingsModel + 变更通知"],
        ["CosyVoice 每句 3~5 秒", "逐句播放有停顿", "预合成下一句或走流式 TTS"],
        ["翻译在插件里", "Demon 自己不能直接产日语", "翻译下沉到 Demon，可配置模型"],
        ["VTS 背景透明靠手动设置", "独立显示仍有背景", "研究 VTS 热键/设置接口自动切换"],
        ["动作映射尚未做", "只有表情和口型", "HotkeysInCurrentModelRequest + TriggerHotkey"],
    ],
    widths=[5.0, 5.5, 5.5],
)

tail = doc.add_paragraph("—— 对应 1.2 开发版代码，后续改动以代码为准 ——")
tail.alignment = WD_ALIGN_PARAGRAPH.CENTER
tail.runs[0].font.size = Pt(9)

doc.save(OUT)
print("saved:", OUT)
