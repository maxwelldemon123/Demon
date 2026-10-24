# -*- coding: utf-8 -*-
"""把 st-gptsovits5-voice 改造成 smartdemon：后端从 9880 换成 Demon 8790。"""

import io, sys

ROOT = r"E:\dshwork\Demon\plugin\smartdemon"
INDEX = f"{ROOT}\\index.js"
LIB = f"{ROOT}\\lib\\tts-text.js"
MANIFEST = f"{ROOT}\\manifest.json"

t = io.open(INDEX, encoding="utf-8").read()
lib = io.open(LIB, encoding="utf-8").read()
mf = io.open(MANIFEST, encoding="utf-8").read()


def rep(text, old, new, label, path=""):
    if old not in text:
        print(f"[MISS] {label}")
        sys.exit(1)
    text = text.replace(old, new, 1)
    print(f"[OK] {label}")
    return text


# ---------- manifest ----------
mf = rep(mf, '"display_name": "GPT-SoVITS v5 角色配音台"', '"display_name": "SmartDemon 配音台"', "manifest 名称")
mf = rep(mf, '"version": "1.0.0"', '"version": "2.0.0"', "manifest 版本")

# ---------- 模块名 / 默认配置 ----------
t = rep(t, "const MODULE = 'gptsovits5_voice';", "const MODULE = 'smartdemon';", "模块名")
t = rep(t, "serverUrl: 'http://127.0.0.1:9880',", "serverUrl: 'http://127.0.0.1:8790',", "默认地址")
t = rep(t, "toast('error', message) : console", "toast('error', message) : console", "noop") if False else t
t = t.replace("fn.call(globalThis.toastr, message, 'GPT-SoVITS v5');", "fn.call(globalThis.toastr, message, 'SmartDemon');")
t = t.replace("console.error(`[GPTSoVITS5] ${message}`)", "console.error(`[SmartDemon] ${message}`)")
t = t.replace("console.log(`[GPTSoVITS5] ${message}`)", "console.log(`[SmartDemon] ${message}`)")
print("[OK] toast 文案")

# ---------- 探活 ----------
t = rep(t, """async function probeServer() {
    const base = baseUrl();
    if (!base) throw new Error('未填写服务端地址');
    const res = await fetch(`${base}/control`, { method: 'GET' });
    if (res.status !== 400 && !res.ok) throw new Error(`HTTP ${res.status}`);
    return res.status;
}""",
"""async function probeServer() {
    const base = baseUrl();
    if (!base) throw new Error('未填写 Demon 地址');
    const res = await fetch(`${base}/healthz`, { method: 'GET' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    try { return (await res.json())?.status === 'ok'; } catch { return true; }
}

/** 从 Demon 拉声线列表（声线由 Demon 管理，插件只引用 id/name） */
async function syncProfilesFromDemon() {
    const base = baseUrl();
    if (!base) return;
    const res = await fetch(`${base}/voice/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const ids = Array.isArray(data?.voice?.profiles) ? data.voice.profiles : [];
    const old = new Map(settings.profiles.map(p => [p.id, p]));
    settings.profiles = ids.map((id) => {
        const prev = old.get(id);
        return {
            id,
            name: prev?.name || id,
            gptWeights: '', sovitsWeights: '', refAudio: '', promptText: '',
            promptLang: prev?.promptLang || 'ja',
        };
    });
    if (data?.voice?.profile) settings.demonDefaultProfile = data.voice.profile;
    save();
    renderProfiles(); renderProfileForm(); renderCharRows(); refreshCurrentCard();
}""", "探活 + 同步声线")

# ---------- 删除 setWeights ----------
start = t.find("async function setWeights(profile, signal) {")
end = t.find("/** 翻译缓存：同语言 + 同文本只翻一次 */", start)
if start > 0 and end > start:
    t = t[:start] + t[end:]
    print("[OK] 删除 setWeights")
else:
    print("[MISS] setWeights 区块")
    sys.exit(1)

# ---------- 合成：改调 Demon ----------
old_body_start = t.find("        const body = {\n            text: speakText,")
old_body_end = t.find("        const blob = await res.blob();", old_body_start)
if old_body_start < 0 or old_body_end < 0:
    print("[MISS] 合成 body 区块")
    sys.exit(1)

new_body = """        // 交给 Demon：只有 text / profile / lang / speed
        const body = {
            text: speakText,
            profile: profile.id,
            lang: target,
            speed,
        };

        const res = await fetch(`${baseUrl()}/voice/speak`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal,
        });

        if (!res.ok) {
            let detail = '';
            try {
                const data = await res.json();
                detail = data?.error?.message || data?.message || '';
            } catch { /* ignore */ }
            throw new Error(`合成失败 HTTP ${res.status}${detail ? '：' + detail : ''}`);
        }

"""
t = t[:old_body_start] + new_body + t[old_body_end:]
print("[OK] 合成改调 Demon")

# 移除 setWeights 调用
t = rep(t, "        await setWeights(profile, signal);\n", "", "移除 setWeights 调用")

# ---------- 档案表单：只读 ----------
old_form_start = t.find("    box.replaceChildren(\n        h('div', { class: 'g5-form-title' }")
old_form_end = t.find("    );\n}\n\nfunction collectProfileInputs", old_form_start)
if old_form_start < 0 or old_form_end < 0:
    print("[MISS] 档案表单区块")
    sys.exit(1)

new_form = """    box.replaceChildren(
        h('div', { class: 'g5-form-title' }, [
            h('span', { text: editing ? `声线：${editing.name || editing.id}` : '声线由 Demon 管理' }),
        ]),
        h('div', { class: 'g5-hint', text: '声线档案（参考音频、权重、提示文本）现在全部放在 Demon 的「语音」页里管理。这里只显示 Demon 提供的声线。' }),
        h('div', { class: 'g5-row-inline' }, [
            h('button', {
                class: 'g5-btn g5-btn-primary', text: '从 Demon 同步声线',
                onclick: () => { syncProfilesFromDemon().catch(e => toast('error', e.message)); },
            }),
            h('button', {
                class: 'g5-btn', text: '试听这条',
                onclick: () => { const p = settings.profiles.find(x => x.id === editingProfileId); if (p) previewProfile(p); },
            }),
        ]),
    """
t = t[:old_form_start] + new_form + t[old_form_end:]
print("[OK] 档案表单改为只读")

# saveProfile 不再校验权重
old_save = t[t.find("function saveProfile() {"):t.find("async function previewProfile(profile)")]
new_save = """function saveProfile() {
    // 声线由 Demon 管理，插件端不再保存档案
    toast('info', '声线请在 Demon 的「语音」页维护，这里点「从 Demon 同步声线」即可');
}

"""
t = t.replace(old_save, new_save, 1)
print("[OK] saveProfile 改为提示")

# ---------- 启动时同步一次 ----------
t = rep(t, "    renderProfiles();\n    renderProfileForm();\n    renderCharRows();\n    refreshCurrentCard();\n    decorateMessages();\n",
"""    renderProfiles();
    renderProfileForm();
    renderCharRows();
    refreshCurrentCard();
    decorateMessages();
    syncProfilesFromDemon().catch((err) => console.warn('[SmartDemon] 同步声线失败', err));
""", "启动时同步声线")

# ---------- lib：cacheKey 带上 profile.id ----------
lib = rep(lib,
"""export function cacheKey(profile, req) {
    return [profile.gptWeights, profile.sovitsWeights, profile.refAudio, profile.promptText, req.textLang, req.speed, req.text]
        .join('\\u0001');
}""",
"""export function cacheKey(profile, req) {
    // Demon 模式下权重/参考音频不在插件里，用 profile.id 区分声线
    return [profile.id, profile.name, req.textLang, req.speed, req.text].join('\\u0001');
}""", "cacheKey 加 profile.id")

# normalizeProfile：只在没有名字时报缺
lib = rep(lib,
"""    const missing = [];
    if (!p.gptWeights) missing.push('GPT 权重');
    if (!p.sovitsWeights) missing.push('SoVITS 权重');
    if (!p.refAudio) missing.push('参考音频');""",
"""    const missing = [];
    // Demon 模式下权重/参考音频由 Demon 管理，插件只要求有名字
    if (!p.name && !p.id) missing.push('名称');""", "normalizeProfile 放宽")

io.open(INDEX, "w", encoding="utf-8", newline="").write(t)
io.open(LIB, "w", encoding="utf-8", newline="").write(lib)
io.open(MANIFEST, "w", encoding="utf-8", newline="").write(mf)
print("改造完成")
