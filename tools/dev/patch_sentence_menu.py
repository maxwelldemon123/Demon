# -*- coding: utf-8 -*-
"""给每条消息加“选句播放”菜单：点列表按钮 → 列出每句 → 点哪句播哪句。"""

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


# 1) 在 speakMessage 后面加“句子菜单”实现
anchor = """function speakLast() {"""
impl = """/* ---- 选句播放 ---- */

let sentMenu = null;

function closeSentMenu() {
    if (sentMenu) { sentMenu.remove(); sentMenu = null; }
}

function chunksForMessage(message) {
    const clean = extractSpeakableText(message?.mes ?? '', {
        stripActions: settings.stripActions,
        readQuotedOnly: settings.readQuotedOnly,
    });
    return splitSentences(clean, { maxLen: Math.max(40, Number(settings.maxChars) || 200) });
}

function openSentenceMenu(mesId, anchorEl) {
    closeSentMenu();
    const message = ctx()?.chat?.[mesId];
    if (!message) return;
    const chunks = chunksForMessage(message);
    if (!chunks.length) { toast('info', '这条消息里没有可朗读的文字'); return; }

    const menu = h('div', { class: 'g5-sent-menu' });
    chunks.forEach((chunk, i) => {
        const item = h('div', {
            class: 'g5-sent-item',
            title: '点这一句只播这一句',
            onclick: (e) => {
                e.stopPropagation();
                const resolved = resolveForMessage(message);
                const cfg = slotConfig(resolved.binding, resolved.slotId);
                const label = `${message.name}（第 ${i + 1} 句）`;
                closeSentMenu();
                speak(chunk, cfg, label);
            },
        }, [
            h('span', { class: 'g5-sent-no', text: String(i + 1) }),
            h('span', { class: 'g5-sent-text', text: chunk.length > 42 ? chunk.slice(0, 42) + '…' : chunk }),
        ]);
        menu.append(item);
    });

    document.body.append(menu);
    const rect = anchorEl.getBoundingClientRect();
    menu.style.left = `${Math.min(window.innerWidth - 300, rect.left)}px`;
    menu.style.top = `${rect.bottom + 6}px`;
    sentMenu = menu;

    setTimeout(() => {
        document.addEventListener('click', closeSentMenu, { once: true });
    }, 0);
}

function speakLast() {"""

rep(anchor, impl, "句子菜单实现")

# 2) decorateMessages 里加一个列表按钮
rep("""        btn.addEventListener('contextmenu', (e) => {
            e.preventDefault(); e.stopPropagation(); cycleAnnotation(mesId);
        });
        host.prepend(btn);""",
"""        btn.addEventListener('contextmenu', (e) => {
            e.preventDefault(); e.stopPropagation(); cycleAnnotation(mesId);
        });
        host.prepend(btn);

        // 选句按钮：弹出句子列表，点哪句播哪句
        const listBtn = h('div', {
            class: 'mes_button g5-narrate-list fa-solid fa-list',
            title: 'SmartDemon：选句播放（列出这条消息的每一句）',
        });
        listBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openSentenceMenu(mesId, listBtn);
        });
        host.prepend(listBtn);""", "列表按钮")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("done")
