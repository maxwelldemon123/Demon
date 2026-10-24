# -*- coding: utf-8 -*-
"""smartdemon 收尾：清理 9880/中继/启动脚本相关的文案和按钮。"""

import io, sys

P = r"E:\dshwork\Demon\plugin\smartdemon\index.js"
t = io.open(P, encoding="utf-8").read()


def rep(old, new, label):
    global t
    if old not in t:
        print(f"[MISS] {label}")
        sys.exit(1)
    t = t.replace(old, new, 1)
    print(f"[OK] {label}")


rep(" * GPT-SoVITS v5 角色配音台 —— SillyTavern 前端扩展 v1.0",
    " * SmartDemon 配音台 —— SillyTavern 前端扩展 v2.0（后端为 Demon 引擎）", "文件头")

rep("""        toast('error', '连不上 GPT-SoVITS。若是 CORS 报错，先启动 server\\\\start-relay.bat，并把握手地址改成 127.0.0.1:9881');""",
    """        toast('error', '连不上 Demon 引擎（127.0.0.1:8790）。请先启动 Demon，确认「状态」页显示监听正常。');""",
    "连接失败提示")

rep("""        text: 'GPT-SoVITS 切音色要换权重（几秒）。同一段台词里两条声线混用时，每换一次都会停顿一下。消息上的 🔊：点=朗读，Shift+点=换声线，Alt+点=标注。',""",
    """        text: '声线与权重由 Demon 管理，切换约 0.3~0.5 秒。消息上的 🔊：点=朗读，Shift+点=换声线，Alt+点=标注。',""",
    "提示文案")

# 删除 showLauncherPath 函数
start = t.find("/**\n * 扩展在本机的真实路径（插件里附带 server")
end = t.find("/* ---- 面板 ---- */", start)
if start > 0 and end > start:
    t = t[:start] + t[end:]
    print("[OK] 删除 showLauncherPath")
else:
    print("[MISS] showLauncherPath 区块")
    sys.exit(1)

rep("""        h('span', { text: 'GPT-SoVITS 服务' }),""", """        h('span', { text: 'Demon 引擎' }),""", "面板标题")

rep("""placeholder: 'http://127.0.0.1:9880'""", """placeholder: 'http://127.0.0.1:8790'""", "占位符")

rep("""            h('button', { class: 'g5-btn', text: '直连 9880', onclick: () => applyServerUrl('http://127.0.0.1:9880') }),
            h('button', { class: 'g5-btn', text: '中继 9881', onclick: () => applyServerUrl('http://127.0.0.1:9881') }),
            h('button', { class: 'g5-btn', text: '一键启动脚本', onclick: () => showLauncherPath() }),""",
    """            h('button', { class: 'g5-btn', text: 'Demon 8790', onclick: () => applyServerUrl('http://127.0.0.1:8790') }),""",
    "按钮组")

rep("""        text: '一键启动：双击插件目录里的 server\\\\start-all.bat（会同时拉起 api_v2 与中继），然后点「中继 9881」→「测试连接」。',""",
    """        text: 'Demon 引擎必须先启动（桌面快捷方式）。语音合成由 Demon 调 GPT-SoVITS，插件这边只负责选句和播放。',""",
    "底部提示")

rep("""h('div', { class: 'g5-header' }, [h('b', { text: 'GPT-SoVITS v5 · 角色配音台' })]),""",
    """            h('div', { class: 'g5-header' }, [h('b', { text: 'SmartDemon · 配音台' })]),""", "抽屉标题")

rep("""    route.textContent = /:9881\\b/.test(baseUrl()) ? '中继模式' : '直连模式';""",
    """    route.textContent = 'Demon 引擎';""", "路由文案 1")

rep("""        if (route) route.textContent = '若是浏览器 CORS 报错 → 用 server\\\\start-relay.bat';""",
    """        if (route) route.textContent = 'Demon 未连接';""", "路由文案 2")

rep("""        title: annotated ? `GPT-SoVITS：本条标注为「${annotated}」` : 'GPT-SoVITS：点=朗读，Shift+点=换声线，Alt+点=标注',""",
    """        title: annotated ? `SmartDemon：本条标注为「${annotated}」` : 'SmartDemon：点=朗读，Shift+点=换声线，Alt+点=标注',""", "消息按钮提示")

rep("""        class: 'g5-toggle', title: 'GPT-SoVITS v5 角色配音台',""",
    """        class: 'g5-toggle', title: 'SmartDemon 配音台',""", "悬浮球提示")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("清理完成")
