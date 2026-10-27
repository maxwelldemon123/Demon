# -*- coding: utf-8 -*-
"""生成《Demon 2.0 技术方案与实施计划书》docx。"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

OUT_DIR = r"E:\dshwork\plan-doc"
OUT = os.path.join(OUT_DIR, "Demon2-技术方案与实施计划书.docx")
os.makedirs(OUT_DIR, exist_ok=True)

EA_FONT = "微软雅黑"
LATIN_FONT = "Segoe UI"


def set_run_font(run, size=None, bold=None, color=None):
    run.font.name = LATIN_FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), EA_FONT)
    rfonts.set(qn("w:ascii"), LATIN_FONT)
    rfonts.set(qn("w:hAnsi"), LATIN_FONT)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = color


doc = Document()

# 页面设置
sec = doc.sections[0]
sec.page_width = Cm(21)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(2.2)
sec.bottom_margin = Cm(2.2)
sec.left_margin = Cm(2.4)
sec.right_margin = Cm(2.4)

# 正文样式
normal = doc.styles["Normal"]
normal.font.name = LATIN_FONT
normal.font.size = Pt(10.5)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), EA_FONT)
normal.paragraph_format.line_spacing = 1.35
normal.paragraph_format.space_after = Pt(4)

for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
    st = doc.styles[name]
    st.font.name = LATIN_FONT
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    rpr = st.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), EA_FONT)
    st.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 8)
    st.paragraph_format.space_after = Pt(6)


def heading(text, level=1):
    p = doc.add_heading(level=level)
    run = p.add_run(text)
    set_run_font(run, size={0: 24, 1: 16, 2: 13, 3: 11.5}.get(level, 11), bold=True,
                 color=RGBColor(0x1F, 0x3A, 0x5F))
    return p


def para(text, size=10.5, bold=False, color=None, align=None, space_after=4):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, color=color)
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    return p


def bullet(text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    run = p.add_run(text)
    set_run_font(run, size=10.5)
    p.paragraph_format.space_after = Pt(2)
    return p


def numbered(text):
    p = doc.add_paragraph(style="List Number")
    run = p.add_run(text)
    set_run_font(run, size=10.5)
    p.paragraph_format.space_after = Pt(2)
    return p


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def table(headers, rows, widths=None, font_size=9, header_fill="DCE6F1"):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        run = p.add_run(h)
        set_run_font(run, size=font_size, bold=True)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        shade(hdr[i], header_fill)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            run = p.add_run(str(val))
            set_run_font(run, size=font_size)
            p.paragraph_format.space_after = Pt(0)
    if widths:
        # 版心宽度 = 21 - 2.4 - 2.4 = 16.2cm，留一点余量，按比例缩放到 16.0
        total = sum(widths) or 1
        scale = 16.0 / total
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w * scale)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def code_block(lines):
    for line in lines:
        p = doc.add_paragraph()
        run = p.add_run(line)
        run.font.name = "Consolas"
        rpr = run._element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        rfonts.set(qn("w:ascii"), "Consolas")
        rfonts.set(qn("w:hAnsi"), "Consolas")
        rfonts.set(qn("w:eastAsia"), EA_FONT)
        run.font.size = Pt(9)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.6)


def footer_page_number():
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)
    set_run_font(run, size=9, color=RGBColor(0x66, 0x66, 0x66))


footer_page_number()

# ============================ 封面 ============================
for _ in range(5):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Demon 2.0")
set_run_font(run, size=34, bold=True, color=RGBColor(0x1F, 0x3A, 0x5F))

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("桌面伴侣 · 技术方案与实施计划书")
set_run_font(run, size=18, color=RGBColor(0x33, 0x33, 0x33))

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Windows 优先 · 香橙派主界面 · 本地模型与语音")
set_run_font(run, size=11, color=RGBColor(0x66, 0x66, 0x66))

for _ in range(8):
    doc.add_paragraph()

meta = [
    ("版本", "v1.0（初稿）"),
    ("日期", "2026-10-24"),
    ("定位", "个人长期工程 · 半职投入（约 25 小时/周）"),
    ("结论", "放弃 Electron，改用 .NET 9 后端 + Web 前端；Windows 用 WebView2，香橙派用 Chromium"),
]
for k, v in meta:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{k}：{v}")
    set_run_font(run, size=10, color=RGBColor(0x44, 0x44, 0x44))
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

# ============================ 目录 ============================
heading("目录", 1)
toc = [
    "1. 摘要与核心结论",
    "2. 背景：为什么放弃 Electron",
    "3. 目标、范围与约束",
    "4. 技术选型",
    "5. 系统架构",
    "6. 关键设计决策",
    "7. 接口协议草案",
    "8. 里程碑与工期",
    "9. 硬件采购清单（BOM）",
    "10. 风险清单与应对",
    "11. 下一步（本周可执行）",
    "附录 A. 现有可复用资产",
    "附录 B. 术语表",
]
for item in toc:
    p = doc.add_paragraph()
    run = p.add_run(item)
    set_run_font(run, size=10.5)
    p.paragraph_format.space_after = Pt(3)

doc.add_page_break()

# ============================ 1 摘要 ============================
heading("1. 摘要与核心结论", 1)
para("本计划书面向一个长期个人工程：以“桌面伴侣”为形态，把大语言模型、本地语音合成（GPT-SoVITS）、Live2D 角色表现、单片机外设与视觉能力整合为一套软件。")
para("上一阶段（Demon 1.0）以 Electron 为壳，把 SillyTavern 作为内嵌内核，验证了「内嵌酒馆 + 插件原样可用 + 自动端口 + 便携打包」这条路可行，但也暴露了一个无法绕开的硬问题：在 Chromium 的进程树里，Python 的 CUDA/torch 初始化会卡死（内存停在约 650MB、单核 100%、永不就绪），而同样的命令由 Shell 进程链启动只需 12~18 秒。同源问题还导致 taskkill 被拒（错误码 128）、schtasks/WMI/%TEMP% 全部受限。")

para("核心结论（本计划书的技术前提）：", bold=True)
bullet("放弃 Electron；改用原生进程宿主（.NET 9）管理本地服务，UI 走 Web 技术。")
bullet("Windows 为第一等公民，必须完整可用；香橙派（Linux ARM64）作为第二阶段的主界面设备。")
bullet("模型全部留在 PC（GPU）；香橙派只做界面、音频采集与硬件桥，不承担推理。")
bullet("聊天内核自研，但兼容 SillyTavern 的角色卡（PNG tEXt / JSON）与世界书格式，保护已有资产。")
bullet("语音沿用本地 GPT-SoVITS（现有权重与两条声线），由独立的“语音监督进程”托管，不由 UI 进程直接拉起。")

para("预计规模：约 500 小时净工作量，按每周 25 小时计约 20 周；含 30% 缓冲约 26 周。", bold=True)

# ============================ 2 背景 ============================
heading("2. 背景：为什么放弃 Electron", 1)
para("Demon 1.0 的技术栈是 Electron 45 + React 外壳 + 内嵌 SillyTavern 1.18（Node 服务）+ 自带 Node 运行时。功能上已经跑通：自动选端口、内嵌酒馆、插件原样加载、语音页、CORS 代理、便携打包。但在“让软件自己管理本地 Python 服务”这件事上，遇到了系统性障碍。")

heading("2.1 实测数据", 2)
table(
    ["启动链", "结果", "结论"],
    [
        ["pwsh → cmd → python", "12~18 秒就绪，显存 2.7GB", "正常"],
        ["Explorer / 登录项 → wscript → cmd → python", "13~18 秒就绪", "正常"],
        ["schtasks → cmd → python", "14.8 秒就绪", "正常"],
        ["Electron → cmd → python", "内存卡 650MB、单核 100%、300 秒不就绪", "失败"],
        ["Electron → wscript(隐藏) → cmd → python", "同上", "失败"],
        ["酒馆 node（Electron 子进程）→ wscript → cmd → python", "同上", "失败"],
        ["Electron 内 taskkill 结束该进程", "返回 128（拒绝访问）", "失败"],
        ["Electron 内 schtasks / WMI / 写 %TEMP%", "一律被拒（EPERM / 拒绝访问）", "失败"],
    ],
    widths=[7.0, 6.2, 3.4],
)

heading("2.2 结论", 2)
para("只要 Python 的祖先进程链里出现 Chromium（Electron）或非 Shell 血统的常驻进程，torch 的初始化就会异常。这不是代码 bug，而是运行环境层面的限制（疑似与进程令牌、作业对象、控制台继承有关），且已穷举 7 种绕行方案（直连 spawn、GUI 启动器、计划任务、explorer+lnk、wscript 隐藏窗口、node 监督进程、cmd 看门狗）均无法在 Electron 内解决。")
para("因此新架构的第一原则是：接管进程的角色必须由原生应用（.NET）承担，UI 只做展示与交互。")

# ============================ 3 目标 ============================
heading("3. 目标、范围与约束", 1)
heading("3.1 产品目标", 2)
bullet("一个可长期使用的桌面伴侣：聊天、语音、角色表现、外设联动、按需视觉。")
bullet("角色卡与世界书可直接复用现有资产；对话体验不弱于酒馆的常用功能。")
bullet("语音本地化：断网可用，延迟可控，两条声线可切换。")
bullet("香橙派接屏作为“第二块屏/主界面”，可脱离 PC 显示与交互（推理仍在 PC）。")

heading("3.2 范围边界", 2)
table(
    ["在范围内", "不在范围内（本期）"],
    [
        ["自研聊天内核（角色卡、世界书、人设、历史、流式输出）", "多人协作、云同步、账号体系"],
        ["本地 TTS 接入与声线管理", "训练新的语音模型（沿用现有权重）"],
        ["Live2D：口型、情绪动作、眨眼呼吸", "3D 角色 / VRM"],
        ["BLE 硬件桥（情绪、口型、按钮、小屏）", "复杂机械控制、电机闭环"],
        ["按需视觉（截图 → VLM 描述）", "实时视频理解、常开摄像头"],
        ["Windows 完整支持；香橙派 Linux 主界面", "macOS / 移动端"],
    ],
    widths=[8.2, 8.2],
)

heading("3.3 约束", 2)
bullet("算力：模型全部在 PC（8GB 显存的 4060 笔记本），香橙派不跑推理。")
bullet("预算：硬件约 1000 元（经济档），后续可升级。")
bullet("投入：每周 20~30 小时，个人开发，需可中断、可分阶段交付。")
bullet("兼容：Windows 必须完整可用；Linux 只要求“界面能跑”，不要求功能对等。")
bullet("资产：继续使用现有 GPT-SoVITS 权重（夜魔两套声线）与角色卡。")

# ============================ 4 选型 ============================
heading("4. 技术选型", 1)
para("评估维度按本工程的实际痛点排序：Windows 兼容性 > 能否管住本地进程 > Live2D 表现力 > 硬件接入（BLE/串口）> 开发速度 > 体积。")

heading("4.1 候选方案对比", 2)
table(
    ["方案", "Windows", "Linux/ARM64", "管进程", "Live2D", "BLE/串口", "工期", "评价"],
    [
        ["Electron", "✅", "✅", "❌ 已实测失败", "✅", "⚠️ 需原生模块", "快", "排除"],
        [".NET 9 + WebView2", "✅ 最佳", "❌ WebView2 无 Linux 版", "✅ 原生", "✅ Web", "✅ 最成熟", "快", "首选（Windows）"],
        [".NET 9 + 浏览器/Chromium", "✅", "✅", "✅ 原生", "✅ Web", "✅", "快", "派端方案"],
        ["Tauri 2", "✅", "⚠️ WebKitGTK 依赖挑版本", "✅ 原生", "✅ Web", "✅ Rust 生态", "中", "备选"],
        ["Avalonia", "✅", "✅", "✅ 原生", "⚠️ 需自绘/嵌 Web", "✅", "中", "备选"],
        ["Flutter", "✅", "✅", "✅", "❌ 生态弱", "⚠️ 插件参差", "快", "不推荐"],
        ["Qt6", "✅", "✅", "✅", "✅ Native SDK", "✅", "慢", "过重"],
    ],
    widths=[3.0, 1.6, 3.0, 2.0, 1.6, 2.0, 1.2, 1.8],
    font_size=8,
)

heading("4.2 最终选型", 2)
para("采用「.NET 9 后端 + React 前端」的双层结构：", bold=True)
bullet("后端：ASP.NET Core（跨平台，Windows 与 Linux ARM64 都能跑），负责聊天内核、语音编排、BLE 桥、CORS 代理、数据存储。")
bullet("前端：React + Vite + pixi-live2d-display，产出纯静态资源。")
bullet("Windows 壳：WebView2（与系统 Edge 同源，体积小、更新由系统负责）。")
bullet("香橙派：Chromium kiosk 模式全屏加载同一套前端（因为 WebView2 没有 Linux 版，这是最省力的等价方案）。")
para("这样做的收益：Windows 端 100% 满足“完全兼容”的要求；派端只换“浏览器外壳”，前端代码零改动；Live2D 与 WebAudio 在两端行为一致。")

para("备选（如果不想在派上跑浏览器）：Avalonia 原生壳 + 内嵌 WebView 仅用于 Live2D。代价是两套 UI 代码与更长的调试周期，不推荐作为首选。", size=9.5, color=RGBColor(0x55, 0x55, 0x55))

# ============================ 5 架构 ============================
heading("5. 系统架构", 1)
heading("5.1 分层", 2)
code_block([
    "┌──────────────────────────── PC (Windows / 后期 Linux) ────────────────────────────┐",
    "│                                                                                  │",
    "│  Demon.Desktop (WebView2 壳)  ──HTTP/WS──┐                                        │",
    "│                                          ▼                                        │",
    "│                        Demon.Server (ASP.NET Core, 端口 8790)                      │",
    "│                        ├─ Chat Engine   角色卡/世界书/人设/历史/token 预算/流式      │",
    "│                        ├─ Voice Bridge  调用 api_v2 (9880) + 内置 CORS 代理 (9881)   │",
    "│                        ├─ Live2D Bridge 情绪→动作映射、口型参数流                    │",
    "│                        ├─ Hardware Hub  BLE/串口 网关（PC 侧调试用）                  │",
    "│                        └─ Storage      SQLite（会话/设置）+ 文件（卡/世界书/立绘）      │",
    "│                                          │                                        │",
    "│  Demon.VoiceSupervisor.exe ──spawn/守护──▶ api_v2.py (9880)  ← 独立进程，Shell 血统  │",
    "│                                                                                  │",
    "└──────────────────────────────────────────────────────────────────────────────────┘",
    "                                   ▲ LAN (HTTP/WebSocket)",
    "                                   │",
    "┌──────────────────────────── 香橙派 (Linux ARM64) ─────────────────────────────────┐",
    "│  Chromium kiosk ── 同一套 React 前端（角色 + 聊天 + Live2D + 触摸操作）              │",
    "│  demon-pi-agent (可选 .NET 或 Python 小服务)                                      │",
    "│      ├─ BLE 中央设备：连接 ESP32-S3（情绪/口型/小屏 + 按钮/传感器）                  │",
    "│      ├─ 音频采集（麦克风）与播放                                                    │",
    "│      └─ 开机自启（systemd）                                                        │",
    "└──────────────────────────────────────────────────────────────────────────────────┘",
])

heading("5.2 为什么把语音监督进程独立出来", 2)
para("上一阶段的核心教训是“谁拉起 Python，决定它能不能跑起来”。新架构里，Demon.VoiceSupervisor 是一个独立的原生可执行文件：")
bullet("由登录项 / systemd 启动，天生属于 Shell 血统，spawn Python 不会踩到 Chromium 的环境问题。")
bullet("对外只暴露一个极小的控制接口（命名管道或本地 HTTP：status / start / stop / restart），UI 与后端通过它指挥语音服务。")
bullet("崩溃自愈：监控 9880 探活，连续失败自动重启，并记录日志。")
bullet("复用已验证结论：wscript 隐藏窗口 + 重定向到文件 + 端口探活，是这台机器上最稳的启动方式。")

heading("5.3 端口与数据", 2)
table(
    ["用途", "端口/位置", "说明"],
    [
        ["Demon.Server HTTP", "127.0.0.1:8790", "前端与后端通信；派通过 LAN 访问 PC:8790"],
        ["CORS 代理", "127.0.0.1:9881", "转发到 9880，补 CORS 头，供浏览器端直接调 TTS"],
        ["GPT-SoVITS api_v2", "127.0.0.1:9880", "沿用现有接口与权重"],
        ["语音监督进程", "命名管道 / 8792", "只允许本机调用"],
        ["数据目录", "%APPDATA%\\Demon2\\", "SQLite + 角色卡 + 日志；派端无数据"],
    ],
    widths=[4.2, 4.2, 8.0],
)

# ============================ 6 设计决策 ============================
heading("6. 关键设计决策", 1)
table(
    ["编号", "决策", "理由"],
    [
        ["D1", "聊天内核自研，但兼容酒馆资产格式", "保住已有角色卡/世界书；同时摆脱其前端与插件依赖"],
        ["D2", "世界书采用“关键词触发 + 递归扫描 + token 预算”三件套", "这是酒馆体验的核心，缺一不可"],
        ["D3", "对话流式输出（SSE）", "首字延迟决定体感；非流式会被用户感知为“卡”"],
        ["D4", "语音走“文本分句 → 逐句合成 → 边播边合成”", "整段合成延迟过高（实测单句 2~7 秒）"],
        ["D5", "Live2D 参数由后端推送（情绪/口型包络），前端只做插值", "保证 PC 与派两端表现一致"],
        ["D6", "BLE 只承载低频控制与小数据（情绪、口型包络 20Hz、按钮）", "BLE 带宽有限，音频不走 BLE"],
        ["D7", "派端不落数据，全部读写 PC", "避免两端数据不一致；派可随时换机"],
        ["D8", "所有外部能力（文本/语音/Live2D/硬件/视觉）统一为“可插拔适配器”", "延续上一版五类接口槽位设计，便于扩展"],
    ],
    widths=[1.2, 7.6, 7.6],
)

# ============================ 7 协议 ============================
heading("7. 接口协议草案", 1)
heading("7.1 后端 HTTP API（前端 ↔ Demon.Server）", 2)
table(
    ["方法", "路径", "说明"],
    [
        ["GET", "/api/health", "健康检查与版本"],
        ["GET", "/api/characters", "角色列表"],
        ["POST", "/api/characters/import", "导入 PNG/JSON 角色卡（解析 tEXt chara）"],
        ["GET", "/api/worldinfo", "世界书列表"],
        ["POST", "/api/worldinfo/import", "导入酒馆世界书 JSON"],
        ["POST", "/api/chat/stream", "发送消息，SSE 返回增量 token 与状态"],
        ["POST", "/api/chat/regenerate", "重生成 / 滑动（swipe）"],
        ["GET", "/api/voice/status", "语音服务状态（经由监督进程）"],
        ["POST", "/api/voice/speak", "文本 → wav（分句合成，返回音频流）"],
        ["POST", "/api/live2d/emotion", "设置情绪（触发动作/表情）"],
        ["GET", "/api/live2d/params", "口型/眨眼参数流（WebSocket 亦可）"],
        ["POST", "/api/hardware/command", "向单片机下发指令（BLE）"],
        ["GET", "/api/hardware/events", "按钮/传感器事件（SSE）"],
    ],
    widths=[1.6, 6.4, 8.4],
    font_size=8.5,
)

heading("7.2 语音服务契约（沿用 api_v2）", 2)
code_block([
    "GET  /control                       → 200/400（400 表示服务活着）",
    "GET  /set_gpt_weights?weights_path=  → 切换 GPT 权重",
    "GET  /set_sovits_weights?weights_path= → 切换 SoVITS 权重",
    "POST /tts {text, text_lang, ref_audio_path, prompt_text, prompt_lang,",
    "           media_type:'wav', streaming_mode:0, speed_factor} → audio/wav",
])

heading("7.3 BLE GATT 草案（派 ↔ ESP32-S3）", 2)
table(
    ["特征", "方向", "UUID（自定义基址）", "载荷"],
    [
        ["情绪", "派 → MCU", "…0001", "uint8：0 平静 / 1 开心 / 2 害羞 / 3 生气 / 4 难过"],
        ["口型", "派 → MCU", "…0002", "uint8 包络，20Hz，0~255"],
        ["音量", "派 → MCU", "…0003", "uint8 0~100"],
        ["小屏文本", "派 → MCU", "…0004", "UTF-8，≤120 字节，分包写入"],
        ["按钮", "MCU → 派", "…0011", "notify：按钮位图"],
        ["传感器", "MCU → 派", "…0012", "notify：温湿度/光线等（TLV）"],
    ],
    widths=[2.6, 2.6, 4.4, 6.8],
    font_size=8.5,
)
para("说明：BLE 音频不可行，语音播放在派端（或 PC）完成；单片机只做“表情与灯光”的低带宽联动。", size=9.5, color=RGBColor(0x55, 0x55, 0x55))

# ============================ 8 里程碑 ============================
heading("8. 里程碑与工期", 1)
para("按每周 25 小时计。工期为净工时估算，另加 30% 缓冲。")
table(
    ["阶段", "内容", "交付物", "工时", "周数"],
    [
        ["M0", "立项、仓库、脚手架（.NET 9 + React + WebView2 壳）", "能打开窗口、加载前端、健康检查通过", "20h", "1"],
        ["M1", "Windows 骨架 + 语音链路", "语音监督进程 + 语音页 + 分句合成播放", "60h", "2.5"],
        ["M2", "聊天内核 MVP", "角色卡导入、人设、历史、流式对话", "120h", "5"],
        ["M3", "世界书 / 记忆 / 正则 / 多角色", "关键词触发、递归、token 预算、总结记忆", "80h", "3"],
        ["M4", "Live2D 完整表现", "口型同步、情绪动作、眨眼呼吸、触摸交互", "70h", "3"],
        ["M5", "硬件与派端", "BLE 桥 + ESP32 固件 + 派 kiosk 主界面", "100h", "4"],
        ["M6", "打磨与交付", "打包、开机自启、文档、崩溃自愈", "50h", "2"],
    ],
    widths=[1.4, 6.0, 6.4, 1.6, 1.4],
    font_size=8.5,
)
para("合计约 500 小时 / 20.5 周；含 30% 缓冲约 26 周（半年）。", bold=True)
para("建议节奏：M1 结束时先给自己一个“能聊天、能出声”的可运行版本，避免长时间没有正反馈。", size=9.5, color=RGBColor(0x55, 0x55, 0x55))

# ============================ 9 BOM ============================
heading("9. 硬件采购清单（BOM）", 1)
para("经济档预算约 1000 元，满足“派接屏做主界面 + BLE 接单片机”的最小闭环。")
table(
    ["类别", "型号建议", "数量", "参考价", "备注"],
    [
        ["主控板", "Orange Pi 5（RK3588S，4GB）", "1", "¥430", "若预算可加，建议 8GB（浏览器 + Live2D 更稳）"],
        ["显示屏", "7 寸 IPS 1024×600，HDMI + USB 触摸", "1", "¥260", "MIPI 屏更薄但驱动麻烦，首选 HDMI"],
        ["电源", "5V/4A DC（5.5×2.5 接口）", "1", "¥40", "派 5 峰值电流较高，别用手机充电器"],
        ["散热", "铝壳 + 风扇（RK3588 被动散热不够）", "1", "¥60", "长时间跑浏览器会热"],
        ["存储", "32GB TF（A2）", "1", "¥30", "系统盘；有条件可用 NVMe"],
        ["单片机", "ESP32-S3 开发板（BLE 5.0）", "1", "¥55", "带屏版本可省小屏"],
        ["音频", "USB 麦克风 + 小音箱（或 3.5mm）", "1", "¥120", "派端采集与播放"],
        ["合计", "", "", "≈¥995", ""],
    ],
    widths=[2.0, 6.0, 1.2, 1.8, 5.4],
    font_size=8.5,
)
para("可选升级：8GB 版 +¥150；10.1 寸触摸屏 +¥150；NVMe 256GB +¥120；摄像头模块 +¥60。", size=9.5, color=RGBColor(0x55, 0x55, 0x55))

# ============================ 10 风险 ============================
heading("10. 风险清单与应对", 1)
table(
    ["风险", "影响", "概率", "应对"],
    [
        ["自研聊天内核工作量超预期（世界书递归、token 预算、人设一致性）", "M2/M3 延期", "高", "先做“最小可用”：单角色、线性历史、关键词触发；递归与预算二期"],
        ["派端 Chromium + Live2D 帧率不足（WebGL 在 ARM 上偏弱）", "主界面卡顿", "中", "限制立绘分辨率与特效；准备“静态立绘 + 眨眼”降级模式；先买板实测再定"],
        ["BLE 在 Linux 上做主从双角色受限", "硬件联动不稳", "中", "派只做 Central（连 MCU），不承担 Peripheral；必要时 MCU 侧加串口兜底"],
        ["GPT-SoVITS 首句延迟高（实测 2~7 秒）", "对话体感差", "高", "分句流水线 + 预合成下一句 + 缓存常用句；必要时引入更轻的 TTS 作为快速通道"],
        ["Windows 与 Linux 行为差异（路径、字体、音频设备）", "移植期返工", "中", "后端全用跨平台 API；音频与路径抽象成适配器；CI 双平台编译"],
        ["角色卡/世界书格式变体多（V2/V3、PNG tEXt、编码）", "导入失败", "中", "导入器做“宽容解析 + 明确报错”，并附格式自检报告"],
        ["单人半职投入，节奏被打断", "整体延期", "高", "里程碑按“可运行”切分；每周留 1 次回归；文档随代码走"],
        ["版权与许可（角色卡、语音权重、Live2D 模型）", "无法公开分发", "低", "默认仅自用；如需分发，逐项确认授权"],
    ],
    widths=[6.2, 3.0, 1.2, 6.2],
    font_size=8.5,
)

# ============================ 11 下一步 ============================
heading("11. 下一步（本周可执行）", 1)
numbered("确定仓库与目录结构：Demon2/{server,web,shell-win,agent-pi,voice-supervisor,docs}。")
numbered("搭 M0 脚手架：.NET 9 Web API + React + WebView2 壳，跑通“窗口加载前端 + /api/health”。")
numbered("把上一版的语音监督逻辑迁移成独立可执行文件，先做到“一键启动 / 停止 / 状态查询”。")
numbered("下单硬件（经济档 BOM），到货前先完成 M1。")
numbered("准备 3 个真实角色卡与 2 份世界书作为回归样本。")
numbered("写一页“聊天内核数据模型”草案（角色、会话、消息、世界书条目、触发记录）。")

# ============================ 附录 ============================
heading("附录 A. 现有可复用资产", 1)
table(
    ["资产", "位置", "复用方式"],
    [
        ["Demon 1.0 工程（Electron）", "E:\\dshwork\\Demon", "UI 设计、日志面板、CORS 代理、语音页逻辑可平移"],
        ["GPT-SoVITS 权重与两条声线", "E:\\GPT-SoVITS-v5-20261005\\...", "直接沿用（xiaod / demon）"],
        ["语音启动脚本与监督思路", "Demon\\release\\Demon\\data\\tmp", "重构为独立 supervisor"],
        ["SillyTavern 角色卡/世界书", "C:\\mylove\\SillyTavern\\data", "作为导入兼容的回归样本"],
        ["CORS 代理实现", "Demon\\electron\\cors-proxy.js", "移植为 .NET 中间件"],
    ],
    widths=[4.6, 6.4, 6.0],
    font_size=8.5,
)

heading("附录 B. 术语表", 1)
table(
    ["术语", "含义"],
    [
        ["Shell 血统", "进程由 Explorer / 登录项 / Shell 等交互式外壳创建，而非由 Chromium 等受限宿主创建"],
        ["世界书（World Info）", "按关键词触发的设定条目集合，进入上下文前需做 token 预算"],
        ["SSE", "Server-Sent Events，服务端单向流式推送，用于逐字输出"],
        ["GATT", "BLE 的通用属性配置文件，定义服务与特征"],
        ["kiosk 模式", "浏览器全屏无边框、无地址栏，用于设备主界面"],
        ["CORS", "浏览器跨源资源共享策略；本地服务未声明时，网页无法直接调用"],
    ],
    widths=[4.0, 12.4],
    font_size=8.5,
)

doc.save(OUT)
print("SAVED", OUT)
print("paragraphs", len(doc.paragraphs), "tables", len(doc.tables))
