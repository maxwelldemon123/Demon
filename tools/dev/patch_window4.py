# -*- coding: utf-8 -*-
"""ControlWindow：按布局自适应大小，长文本换行。"""

import io, sys

P = r"E:\dshwork\Demon\src\ui\ControlWindow.cpp"
t = io.open(P, encoding="utf-8").read()


def rep(old, new, label):
    global t
    if old not in t:
        print(f"[MISS] {label}")
        sys.exit(1)
    t = t.replace(old, new, 1)
    print(f"[OK] {label}")


rep("""    setWindowTitle(QStringLiteral("Demon"));
    resize(560, 440);
    setMinimumSize(520, 400);

    if (QScreen* screen = QGuiApplication::primaryScreen()) {
        const QRect area = screen->availableGeometry();
        move(area.center() - rect().center());
    }""",
    """    setWindowTitle(QStringLiteral("Demon"));
    setMinimumWidth(600);""", "去掉固定尺寸")

rep("""    m_listenLabel->setTextInteractionFlags(Qt::TextSelectableByMouse);""",
    """    m_listenLabel->setTextInteractionFlags(Qt::TextSelectableByMouse);
    m_listenLabel->setWordWrap(true);
    m_upstreamLabel->setWordWrap(true);
    m_upstreamLabel->setTextInteractionFlags(Qt::TextSelectableByMouse);
    m_modelLabel->setWordWrap(true);""", "长文本换行")

rep("""    connect(m_autoPlayBox, &QCheckBox::toggled, this, [this](bool checked) {
        if (m_updating) {
            return;
        }
        if (m_callbacks.setAutoPlay) {
            m_callbacks.setAutoPlay(checked);
        }
    });
}""",
    """    connect(m_autoPlayBox, &QCheckBox::toggled, this, [this](bool checked) {
        if (m_updating) {
            return;
        }
        if (m_callbacks.setAutoPlay) {
            m_callbacks.setAutoPlay(checked);
        }
    });

    // 按布局的实际需要定尺寸，避免按钮被裁掉
    adjustSize();
    resize(qMax(600, sizeHint().width()), qMax(460, sizeHint().height()));
}""", "自适应尺寸")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("patched")
