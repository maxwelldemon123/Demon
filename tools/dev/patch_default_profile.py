# -*- coding: utf-8 -*-
"""未绑定角色时回退到 Demon 的默认声线。"""

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


rep("""async function speak(rawText, cfg, label) {
    if (!settings.enabled) return;
    if (!cfg?.profile) {
        toast('info', `「${label || '该角色'}」还没绑定音色档案，先在面板里选一个`);
        return;
    }
""",
"""function defaultProfile() {
    if (!settings) return null;
    const id = settings.demonDefaultProfile;
    return settings.profiles.find(p => p.id === id) || settings.profiles[0] || null;
}

async function speak(rawText, cfg, label) {
    if (!settings.enabled) return;

    // 角色没绑定时，用 Demon 的默认声线兜底
    let useCfg = cfg;
    if (!useCfg?.profile) {
        const fallback = defaultProfile();
        if (fallback) {
            useCfg = { ...(useCfg || {}), profile: fallback, speed: useCfg?.speed ?? 1, textLang: useCfg?.textLang ?? 'auto' };
        }
    }
    if (!useCfg?.profile) {
        toast('info', `「${label || '该角色'}」还没绑定音色档案，先在面板里选一个`);
        return;
    }
""", "默认声线兜底")

rep("""        let pending = guard(synthesize(chunks[0], cfg.profile, cfg, s.controller.signal));""",
    """        let pending = guard(synthesize(chunks[0], useCfg.profile, useCfg, s.controller.signal));""",
    "合成第一句用兜底配置")

rep("""                pending = guard(synthesize(chunks[i + 1], cfg.profile, cfg, s.controller.signal));""",
    """                pending = guard(synthesize(chunks[i + 1], useCfg.profile, useCfg, s.controller.signal));""",
    "后续句子用兜底配置")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("done")
