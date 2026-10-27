# -*- coding: utf-8 -*-
"""在 v1.1 生成脚本基础上插入「推理管线」与「与酒馆集成」两章，输出 v1.2。"""

import io, os, re

SRC = r"E:\dshwork\plan-doc\build_plan_v11.py"
DST = r"E:\dshwork\plan-doc\build_plan_v12.py"

src = io.open(SRC, encoding="utf-8").read()

# 1) 改输出文件名与封面版本号
src = src.replace(
    'OUT = os.path.join(OUT_DIR, "Demon2-技术方案与实施计划书-v1.1.docx")',
    'OUT = os.path.join(OUT_DIR, "Demon2-技术方案与实施计划书-v1.2.docx")'
)
src = src.replace('"技术方案与实施计划书 · v1.1"', '"技术方案与实施计划书 · v1.2"')
src = src.replace('("版本", "v1.1（替代 v1.0）")', '("版本", "v1.2（替代 v1.1）")')

# 2) 后续章节重新编号（先改大写编号，避免与新插入的冲突）
renum = [
    ('heading("4. 系统架构（1.0）", 1)', 'heading("6. 系统架构（1.0）", 1)'),
    ('heading("5. 2.0：Live2D 接入方案（ExAPI）", 1)', 'heading("7. 2.0：Live2D 接入方案（ExAPI）", 1)'),
    ('heading("6. 1.0 排期（一周 / 2 人 / 约 80h）", 1)', 'heading("8. 1.0 排期（一周 / 2 人 / 约 80h）", 1)'),
    ('heading("7. 风险与应对", 1)', 'heading("9. 风险与应对", 1)'),
    ('heading("8. 下一步（等指令）", 1)', 'heading("10. 下一步（等指令）", 1)'),
]
for a, b in renum:
    assert a in src, a
    src = src.replace(a, b)

NEW_CHAPTERS = '''

# ============================ 4 推理管线 ============================
heading("4. 推理管线复刻规格", 1)
para("酒馆的“后端推理”其实是两层：模型前向计算，以及把它包起来的生成管线。C++ 要复刻的是后者；前者直接调 API 或嵌入 llama.cpp。")

heading("4.1 管线环节与工时", 2)
table(
    ["环节", "内容", "难度", "单人估时"],
    [
        ["宏替换", "{{char}} {{user}} {{random::a::b}} {{time}} {{date}}、聊天变量", "低", "2~3 天"],
        ["人设注入", "description / personality / scenario / system_prompt", "低", "1 天"],
        ["世界书注入", "按 position（角色前/后/指定深度/示例区）、depth、role 插入", "中高", "4~6 天"],
        ["示例对话", "mes_example 按 <START> 分段，可被世界书插入", "中", "2 天"],
        ["历史与预算", "context size、max_tokens、超限裁剪（保 system 与最近 N 轮）", "中", "2~3 天"],
        ["模板包装", "instruct/context 模板（ChatML、Llama3、Alpaca…）、system 位置", "中", "2 天"],
        ["流式生成", "SSE 解析、增量回调、stop 字符串、continue 拼接", "低", "2 天"],
        ["重生成/滑动", "regenerate、swipe、branch", "低", "2 天"],
        ["正则后处理", "输出前/后的 regex 脚本（作用域与顺序）", "中", "2 天"],
        ["群聊调度", "多角色轮流、激活策略、talkativeness", "中", "3~4 天"],
        ["采样参数", "temperature / top_p / top_k / 重复惩罚", "低", "只透传，不自研"],
    ],
    widths=[2.4, 7.6, 1.4, 2.4],
)
para("合计约 18~23 人天。两人并行约 2 周可做出可用管线；1.0 只取其中一半（宏、人设、示例、历史预算、模板、流式、重生成），约 8~10 人天。", bold=True)

heading("4.2 能对齐的与只能近似的", 2)
table(
    ["项目", "结论"],
    [
        ["prompt 结构、注入位置、裁剪顺序", "✅ 可逐字节对齐（用黄金 prompt 对照测试）"],
        ["世界书触发集合", "✅ 可对齐（同一套 key/逻辑/概率/预算规则）"],
        ["token 计数", "⚠️ 不可能完全一致；做法：内置近似估算 + 可插拔 tokenizer"],
        ["采样质量", "⚠️ 取决于模型与 API，管线只负责把参数传对"],
        ["扩展能力（向量记忆、摘要、TTS 插件）", "❌ 不在核心；酒馆里也是前端插件"],
    ],
    widths=[6.0, 10.0],
)

heading("4.3 C++ 模块与验收方法", 2)
code_block([
    "inference/",
    "  Macros.cpp               宏与变量替换",
    "  PromptAssembler.cpp      system + 人设 + 世界书 + 示例 + 历史 + 模板",
    "  ContextBudget.cpp        token 估算与裁剪",
    "  InstructTemplate.cpp     模板解析（导入 preset 或内置）",
    "  StreamParser.cpp         SSE + stop + continue",
    "  GenerationController.cpp generate / regenerate / swipe / stop",
    "  RegexProcessor.cpp       输出前后处理",
    "  GroupOrchestrator.cpp    群聊轮次（1.0 不做）",
])
para("验收不靠肉眼：用酒馆对同一输入生成的 prompt 原文作为基线，C++ 版输出逐行 diff，一致才算通过。这能把“感觉差不多”变成“确实一样”。", bold=True)

# ============================ 5 与酒馆集成 ============================
heading("5. 与 SillyTavern 的集成方式", 1)
para("先澄清一个容易误解的点：酒馆的生成逻辑（拼 prompt、世界书激活、历史管理）跑在**浏览器端**，服务端只负责文件读写、静态资源、LLM 代理与分词。所以“调酒馆后端”拿不到推理逻辑，只能拿到数据与代理能力。")

heading("5.1 三种集成路线", 2)
table(
    ["路线", "做法", "优点", "缺点", "建议"],
    [
        ["A. 文件直读", "直接解析 characters/chats/worlds/*.json(l)", "零依赖、零耦合、ST 不用运行", "需自己实现解析与触发引擎", "**1.0 采用**"],
        ["B. HTTP API", "调用 ST 的 /api/*（角色、聊天、世界书、分词、LLM 代理）", "复用其数据读写与 tokenizer", "需要 ST 常驻、有 CSRF、接口随版本变化", "作为可选数据源"],
        ["C. 无头浏览器驱动", "用 WebView2/Playwright 打开 ST 页面，注入 JS 调 generateQuietPrompt", "能复用其全部生成逻辑", "重、脆、难调试、依赖 UI", "不采用"],
    ],
    widths=[2.4, 5.6, 3.6, 4.2, 2.2],
)

heading("5.2 酒馆可复用的端点（若走路线 B）", 2)
table(
    ["端点", "用途"],
    [
        ["GET /csrf-token", "拿到 CSRF token，后续请求需带 X-CSRF-Token"],
        ["GET /api/characters/all|get", "角色列表与详情"],
        ["GET /api/chats/get|search", "读取会话"],
        ["POST /api/chats/save", "写回会话（jsonl）"],
        ["GET /api/worldinfo/get|list", "世界书条目"],
        ["GET /api/settings/get", "设置（只取子集）"],
        ["POST /api/tokenizers/*/encode", "精确 token 计数（比自研估算准）"],
        ["POST /api/backends/chat-completions/generate", "LLM 代理（复用其密钥与 CORS 处理）"],
    ],
    widths=[7.4, 8.6],
)

heading("5.3 推荐架构：数据源可插拔", 2)
code_block([
    "IDataSource（接口）",
    "  ├─ FileSource     直接读酒馆目录（默认，无需 ST 运行）",
    "  ├─ HttpSource     酒馆在跑时走 /api/*（可选，用于同步）",
    "  └─ SqliteSource   我们自己导入后的规范化库（运行时只用它）",
])
para("这样 1.0 用 FileSource → SqliteSource；以后想和酒馆共用数据，只是多实现一个 HttpSource，核心不动。")

heading("5.4 风险与对策", 2)
bullet("CSRF 与登录态：HttpSource 必须先取 token；失败要降级到 FileSource。")
bullet("并发写：酒馆开着时可能同时写同一份 jsonl，采用“只读同步 + 我们自己的库为写目标”。")
bullet("版本漂移：端点与字段用白名单 + 宽容解析，解析失败给明确错误。")
bullet("tokenizer：HTTP 往返慢，运行时用本地近似；仅在“标定”时调用酒馆的分词端点校准系数。")

'''

anchor = '# ============================ 4 架构 ============================'
assert anchor in src
src = src.replace(anchor, NEW_CHAPTERS + '\n# ============================ 6 架构 ============================')

io.open(DST, "w", encoding="utf-8").write(src)
print("WROTE", DST, len(src))
