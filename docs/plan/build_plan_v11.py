# -*- coding: utf-8 -*-
"""生成《Demon 2.0 技术方案与实施计划书 v1.1》——Qt C++ / 酒馆兼容数据层。"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

OUT_DIR = r"E:\dshwork\plan-doc"
OUT = os.path.join(OUT_DIR, "Demon2-技术方案与实施计划书-v1.1.docx")
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

sec = doc.sections[0]
sec.page_width = Cm(21)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(2.2)
sec.bottom_margin = Cm(2.2)
sec.left_margin = Cm(2.4)
sec.right_margin = Cm(2.4)

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


def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(text)
    set_run_font(run, size=10.5)
    p.paragraph_format.space_after = Pt(2)


def numbered(text):
    p = doc.add_paragraph(style="List Number")
    run = p.add_run(text)
    set_run_font(run, size=10.5)
    p.paragraph_format.space_after = Pt(2)


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def table(headers, rows, widths=None, font_size=8.5, header_fill="DCE6F1"):
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
        run.font.size = Pt(8.5)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.5)


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
run = p.add_run("技术方案与实施计划书 · v1.1")
set_run_font(run, size=18, color=RGBColor(0x33, 0x33, 0x33))

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Qt C++ · 酒馆兼容数据层 · Live2D 交给 Live2DViewerEX(ExAPI)")
set_run_font(run, size=11, color=RGBColor(0x66, 0x66, 0x66))

for _ in range(7):
    doc.add_paragraph()

meta = [
    ("版本", "v1.1（替代 v1.0）"),
    ("日期", "2026-10-24"),
    ("团队", "2 人 · 合计约 80 小时/周"),
    ("1.0 目标", "一周内：PC 独立可聊、可出声、可导入酒馆资产（不含 Live2D）"),
    ("2.0 目标", "两个月内：Live2D 角色表现（走 Live2DViewerEX ExAPI）"),
]
for k, v in meta:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{k}：{v}")
    set_run_font(run, size=10, color=RGBColor(0x44, 0x44, 0x44))
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

# ============================ 1 路线图 ============================
heading("1. 版本路线图", 1)
para("本版最大的变化：放弃 Electron 与 WebView2 方案，改为 Qt 6 / C++ 原生桌面程序；Live2D 不再自研，交给 Live2DViewerEX 通过 ExAPI 控制。")

table(
    ["版本", "目标", "范围要点", "验收标准", "预估"],
    [
        ["1.0", "PC 独立可用", "酒馆数据层（角色卡/聊天/世界书/人设）+ 流式聊天 + TTS + 托盘输入条", "导入真实卡能聊、能出声", "1 周 / 80h"],
        ["2.0", "PC 上 Live2D 交互", "ExAPI WebSocket 客户端：表情、动作、气泡、推音频、点角色触发", "角色会动、口型跟上、点击有反应", "3~4 周 / 120h"],
        ["3.0", "PC ↔ 单片机", "Qt SerialPort/BLE → STM32F103/G431：情绪、口型、按钮", "板子跟着表情动", "2~3 周"],
        ["4.0", "树莓派 Demon", "派上只做交互与显示（Qt 交叉编译或轻量方案）", "派接屏能跑", "3~4 周"],
        ["5.0", "三端联动", "PC 跑模型 / 派接云 / 单片机执行", "全链路可用", "4 周+"],
        ["6.0", "做减法", "体积、内存、启动时间优化", "包体与占用达标", "2 周"],
    ],
    widths=[1.2, 3.2, 7.4, 5.6, 2.4],
)

para("说明：1.0 不含 Live2D（按你的要求后移到 2.0）；树莓派与单片机相关内容在对应版本前不写代码。", size=9.5, color=RGBColor(0x55, 0x55, 0x55))

# ============================ 2 技术选型 ============================
heading("2. 技术选型（本版结论）", 1)
table(
    ["层", "选择", "理由"],
    [
        ["语言", "C++20", "Qt 原生、性能与打包可控；与 STM32 侧工具链一致"],
        ["GUI", "Qt 6 Widgets（少量 QML 可选）", "桌面稳定性最好；透明置顶窗口与托盘成熟"],
        ["数据", "QtSql + SQLite", "单文件库、零部署；导入后规范化存储"],
        ["网络", "QNetworkAccessManager（SSE 流式）/ QWebSocket", "原生支持流式与 ExAPI"],
        ["JSON", "QJsonDocument / QJsonObject", "无需第三方库"],
        ["PNG 元数据", "自写 chunk 解析（约 100 行）", "读 tEXt:chara，不引入 libpng 依赖"],
        ["语音", "HTTP 调本地 GPT-SoVITS（api_v2, 9880）", "沿用现有权重与两条声线"],
        ["Live2D", "Live2DViewerEX ExAPI（WebSocket JSON）", "不自研渲染；2.0 才接"],
        ["硬件", "Qt SerialPort（3.0）", "STM32 走串口最稳"],
    ],
    widths=[2.4, 6.4, 8.0],
)

para("明确不采用：Electron（进程环境限制已实测）、WebView2（1.0 不需要网页）、Web 前端（无渲染需求后成为负担）。", size=9.5, color=RGBColor(0x55, 0x55, 0x55))

# ============================ 3 数据层 ============================
heading("3. 酒馆兼容数据层（1.0 的核心）", 1)
para("这是本版的重点：先把“能读懂酒馆的数据”做扎实，UI 与聊天才有意义。所有解析都写成独立模块，配单元测试，不依赖界面。")

heading("3.1 需要兼容的四类数据", 2)
table(
    ["数据", "位置与格式", "要点", "难度"],
    [
        ["角色卡", "characters/*.png（tEXt 块 key=chara，base64 JSON V2/V3）或 *.json", "字段：name/description/personality/scenario/first_mes/mes_example/creator_notes/tags；V3 有 data.extensions", "低"],
        ["聊天记录", "chats/<角色>/<会话>.jsonl，每行一条 JSON", "首行含 user_name/character_name/create_date/chat_metadata；其余含 name/is_user/is_system/send_date/mes/extra", "低"],
        ["世界书", "worlds/*.json → entries{uid:{...}}", "key/keysecondary/selective/selectiveLogic/order/position/depth/role/probability/useProbability/disable/group/recursion 开关", "中"],
        ["设置与预设", "settings.json（模型、instruct/context 模板、人设、正则、世界书全局参数）", "体量巨大且版本漂移，只导入需要的子集", "中"],
    ],
    widths=[2.0, 6.6, 7.4, 1.4],
)

heading("3.2 C++ 模块划分", 2)
code_block([
    "stcore/                        静态库，无 UI 依赖，可单测",
    "  CardParser.cpp/.h            PNG chunk 解析 + base64 + JSON（V2/V3）",
    "  ChatStore.cpp/.h             jsonl 读写、元数据、增量追加",
    "  WorldInfo.cpp/.h             解析 + 触发引擎（关键词/次级键/逻辑/概率/位置/深度/预算）",
    "  PersonaStore.cpp/.h          用户人设",
    "  PresetStore.cpp/.h           instruct / context 模板（可选导入）",
    "  SettingsImport.cpp/.h        settings.json 子集导入",
    "  Db.cpp/.h                    SQLite 规范化表（cards/chats/messages/wi/settings）",
    "  PromptBuilder.cpp/.h         组装 system + 世界书 + 历史 + 模板",
    "app/                           Qt Widgets",
    "  TrayIcon / InputBar / ChatWindow / SettingsDialog",
    "services/",
    "  LlmClient.cpp                OpenAI 兼容 SSE 流式",
    "  TtsClient.cpp                api_v2 分句合成 + 播放队列",
])

heading("3.3 触发引擎（世界书）的最小实现", 2)
bullet("一级：key 命中（大小写/整词开关）。")
bullet("二级：keysecondary + selectiveLogic（AND_ANY / AND_ALL / NOT_ANY / NOT_ALL）。")
bullet("过滤：disable、probability（useProbability 时按权重随机）、group 互斥。")
bullet("排序：order 升序，按 position（角色前/后、指定深度、示例区）插入。")
bullet("预算：总 token 上限（默认 800），超限按 order 截断。")
bullet("1.0 明确不做：递归扫描（recursion）、自动化 ID、跨角色世界书联动。")

heading("3.4 数据层的验收（做完才谈 UI）", 2)
numbered("导入 3 张真实角色卡（含小鲸鱼娘那张 PNG），字段与酒馆解析结果逐项一致。")
numbered("读取一份 500 条消息的 jsonl，读写往返除新增元数据外无差异。")
numbered("对 10 条测试输入，世界书触发集合与酒馆一致（人工比对）。")
numbered("世界书 100 条、预算 800 token 时，注入内容不超限且有稳定顺序。")
numbered("数据库往返：导入 → 关闭 → 重开，数据完整。")

# ============================ 4 架构 ============================
heading("4. 系统架构（1.0）", 1)
code_block([
    "┌──────────────────────────── Windows PC ────────────────────────────┐",
    "│  Demon.exe (Qt Widgets)                                           │",
    "│   ├─ 托盘图标 / 全局热键                                            │",
    "│   ├─ 输入条（无边框、置顶、可半透明）                                 │",
    "│   ├─ 聊天窗口（消息流、重生成、停止）                                 │",
    "│   └─ 设置（模型地址/Key、声线、世界书开关）                            │",
    "│                                                                    │",
    "│  stcore（静态库）                                                   │",
    "│   ├─ CardParser / ChatStore / WorldInfo / PromptBuilder             │",
    "│   └─ SQLite（cards, chats, messages, worldinfo, settings）           │",
    "│                                                                    │",
    "│  services                                                          │",
    "│   ├─ LlmClient  ──HTTPS/SSE──▶ 云端或本地 LLM                        │",
    "│   └─ TtsClient  ──HTTP──▶ api_v2 (127.0.0.1:9880) ──▶ WAV ──▶ 播放   │",
    "│                                                                    │",
    "│  （2.0 接入）Live2DViewerEX ◀──WebSocket(ExAPI)── 表情/动作/气泡/音频  │",
    "│  （3.0 接入）STM32F103/G431 ◀──Qt SerialPort── 情绪/口型/按钮         │",
    "└────────────────────────────────────────────────────────────────────┘",
])

# ============================ 5 ExAPI ============================
heading("5. 2.0：Live2D 接入方案（ExAPI）", 1)
para("Live2DViewerEX 官方文档提供 ExAPI（第三方开发者），采用 WebSocket + JSON 消息，格式为 {\"msg\": 消息码, \"msgId\": 序号, \"data\": ...}。以下为文档中与本项目相关的消息码。")
table(
    ["消息码", "能力", "本项目用法"],
    [
        ["10000 / 10001", "注册 / 取消模型事件监听", "连接后注册，接收点击事件"],
        ["10002", "接收事件（type=0 为点击）", "点角色 → 触发一句问候或打开输入条"],
        ["11000", "显示气泡文本（可带按钮，返回所选项）", "对话气泡 / 选项式回复"],
        ["13000 / 13100", "设置 / 移除模型（*.model.json）", "切换角色"],
        ["13200", "触发动作（group:motion）", "情绪 → 动作组"],
        ["13300 / 13302", "设置 / 清除表情（expId）", "情绪 → 表情"],
        ["13500 / 13501", "播放 / 停止声音（文件或 base64，3 频道）", "**TTS 音频直接推给它**，口型由它跟音频"],
        ["12010 / 14000", "设置背景 / 特效（雨、雪）", "场景氛围（可选）"],
        ["13400", "设置模型位置", "多显示器摆位"],
    ],
    widths=[3.0, 7.4, 6.6],
)
para("由此 2.0 的工作量从“自研渲染”降为“写一个 WebSocket 客户端 + 情绪映射表”，预计 3~4 周内可完成（含调试与降级方案）。", bold=True)

# ============================ 6 排期 ============================
heading("6. 1.0 排期（一周 / 2 人 / 约 80h）", 1)
table(
    ["天", "内容", "负责", "交付物"],
    [
        ["D1", "工程脚手架（CMake + Qt6 + SQLite）、stcore 空壳、单测框架", "两人", "能编译、测试跑通"],
        ["D2", "CardParser（PNG tEXt + JSON V2/V3）", "A", "3 张卡解析正确"],
        ["D2-D3", "ChatStore（jsonl 读写）+ Db（SQLite）", "B", "导入/往返测试通过"],
        ["D3", "WorldInfo 解析 + 最小触发引擎", "A", "10 条用例命中正确"],
        ["D4", "PromptBuilder + LlmClient（SSE 流式）", "B", "命令行能流式对话"],
        ["D5", "TtsClient（分句合成 + 播放队列 + 声线切换）", "A", "能出声"],
        ["D6", "Qt UI：托盘 + 输入条 + 聊天窗口 + 设置", "B", "可日常使用"],
        ["D7", "联调、回归、打包（windeployqt）、文档", "两人", "1.0 验收"],
    ],
    widths=[1.4, 7.0, 1.4, 6.2],
)

# ============================ 7 风险 ============================
heading("7. 风险与应对", 1)
table(
    ["风险", "影响", "概率", "应对"],
    [
        ["1 周内数据层 + UI 做不完", "1.0 延期", "高", "D3 前若数据层未过，UI 降级为“命令行 + 托盘输入条”，窗口后补"],
        ["酒馆 settings.json 结构漂移", "导入失败", "中", "只导入白名单字段；解析失败给明确报错并跳过"],
        ["世界书触发与酒馆不一致", "体感差", "中", "抽 10 条真实对话做对照；先保证一级+二级命中，递归后置"],
        ["TTS 首句延迟 2~7 秒", "对话卡顿", "高", "分句流水线 + 预取下一句 + 常用句缓存"],
        ["Live2DViewerEX ExAPI 版本差异", "2.0 返工", "中", "先写探测脚本打印版本与能力；适配层隔离"],
        ["Viewer 口型来源不确定（系统音频/麦克风）", "口型对不上", "中", "2.0 第一天就验证；不行则改用 13500 推音频由它内部驱动"],
        ["Qt 透明置顶窗口在 Windows 上焦点/穿透问题", "输入条不好用", "中", "用 WS_EX_NOACTIVATE + WM_NCHITTEST 方案，预留一天调"],
        ["单片机侧进度依赖朋友", "3.0 阻塞", "低", "先定协议与帧格式，PC 侧用模拟设备联调"],
    ],
    widths=[6.4, 3.0, 1.2, 6.2],
)

# ============================ 8 下一步 ============================
heading("8. 下一步（等指令）", 1)
numbered("安装 Qt 6（含 MSVC 工具链）与 CMake；确认 Qt 版本与编译器组合。")
numbered("建仓库 Demon2/{stcore,app,services,tests,pi(占位)}。")
numbered("先写 CardParser + 单测（这是整个数据层的地基）。")
numbered("准备 3 张角色卡、1 份 500 条聊天、1 份世界书作为回归样本。")

# ============================ 附录 ============================
heading("附录 A. 酒馆数据格式速查", 1)
table(
    ["文件", "关键字段"],
    [
        ["角色卡 JSON（V2）", "spec/spec_version/data{name,description,personality,scenario,first_mes,mes_example,creator_notes,system_prompt,post_history_instructions,alternate_greetings,character_book,tags,creator,character_version,extensions}"],
        ["PNG 卡", "chunk 类型 tEXt，keyword=chara，text=base64(UTF-8 JSON)；V3 另有 ccv3"],
        ["聊天 jsonl 首行", "user_name, character_name, create_date, chat_metadata{favorites, integrity, ...}"],
        ["聊天 jsonl 消息行", "name, is_user, is_system, send_date, mes, extra{api, model, ...}"],
        ["世界书条目", "key[], keysecondary[], comment, content, constant, selective, selectiveLogic, order, position, depth, role, probability, useProbability, disable, excludeRecursion, preventRecursion, matchWholeWords, caseSensitive, group"],
    ],
    widths=[3.6, 12.4],
)

heading("附录 B. 术语", 1)
table(
    ["术语", "含义"],
    [
        ["tEXt chunk", "PNG 的文本元数据块，角色卡的 JSON 就藏在这里"],
        ["jsonl", "每行一个 JSON 的文本格式，酒馆用它存聊天记录"],
        ["ExAPI", "Live2DViewerEX 提供给第三方程序的 WebSocket 控制接口"],
        ["SSE", "服务端推送流，用于逐字显示模型输出"],
        ["instruct 模板", "把对话包装成模型能理解的指令格式（如 ChatML、Alpaca）"],
    ],
    widths=[3.6, 12.4],
)

doc.save(OUT)
print("SAVED", OUT)
print("paragraphs", len(doc.paragraphs), "tables", len(doc.tables))
