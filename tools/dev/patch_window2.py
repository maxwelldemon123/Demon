# -*- coding: utf-8 -*-
"""ControlWindow 布局修正：居中、合理尺寸、按钮两行。"""

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


rep('#include <QDesktopServices>', '#include <QDesktopServices>\n#include <QGridLayout>\n#include <QGuiApplication>\n#include <QScreen>', "includes")

rep("""    setWindowTitle(QStringLiteral("Demon"));
    setMinimumWidth(460);""",
    """    setWindowTitle(QStringLiteral("Demon"));
    resize(560, 440);
    setMinimumSize(520, 400);

    if (QScreen* screen = QGuiApplication::primaryScreen()) {
        const QRect area = screen->availableGeometry();
        move(area.center() - rect().center());
    }""", "尺寸与居中")

rep("""    auto* buttons = new QHBoxLayout();
    auto* copyButton = new QPushButton(QStringLiteral("复制接口地址"), this);
    auto* logButton = new QPushButton(QStringLiteral("打开日志"), this);
    auto* cfgButton = new QPushButton(QStringLiteral("配置目录"), this);
    auto* reloadButton = new QPushButton(QStringLiteral("重载配置"), this);
    buttons->addWidget(copyButton);
    buttons->addWidget(logButton);
    buttons->addWidget(cfgButton);
    buttons->addWidget(reloadButton);
    root->addLayout(buttons);""",
    """    auto* buttons = new QGridLayout();
    auto* copyButton = new QPushButton(QStringLiteral("复制接口地址"), this);
    auto* logButton = new QPushButton(QStringLiteral("打开日志"), this);
    auto* cfgButton = new QPushButton(QStringLiteral("配置目录"), this);
    auto* reloadButton = new QPushButton(QStringLiteral("重载配置"), this);
    buttons->addWidget(copyButton, 0, 0);
    buttons->addWidget(logButton, 0, 1);
    buttons->addWidget(cfgButton, 1, 0);
    buttons->addWidget(reloadButton, 1, 1);
    root->addLayout(buttons);""", "按钮网格")

rep("""    connect(copyButton, &QPushButton::clicked, this, [this]() {
        // 复制当前监听地址对应的接口 URL
        const QString text = m_listenLabel->text().trimmed();
        QGuiApplication::clipboard()->setText(text + QStringLiteral("/v1"));
    });""",
    """    connect(copyButton, &QPushButton::clicked, this, [this, copyButton]() {
        // 复制当前监听地址对应的接口 URL
        const QString text = m_listenLabel->text().trimmed();
        QGuiApplication::clipboard()->setText(text + QStringLiteral("/v1"));
        copyButton->setText(QStringLiteral("已复制 ✓"));
        QTimer::singleShot(1500, copyButton, [copyButton]() {
            copyButton->setText(QStringLiteral("复制接口地址"));
        });
    });""", "复制反馈")

rep('#include <QVBoxLayout>', '#include <QVBoxLayout>\n#include <QTimer>', "include QTimer")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("layout patched")
