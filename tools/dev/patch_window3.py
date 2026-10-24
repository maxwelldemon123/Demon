# -*- coding: utf-8 -*-
"""窗口居中（show 之后按实际尺寸）+ 托盘菜单加入口。"""

import io, sys

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()


def rep(old, new, label):
    global t
    if old not in t:
        print(f"[MISS] {label}")
        sys.exit(1)
    t = t.replace(old, new, 1)
    print(f"[OK] {label}")


rep("""    updateWindowStatus();
    m_window->show();""",
    """    updateWindowStatus();
    m_window->show();

    // show() 之后尺寸才最终确定，此时再居中
    if (QScreen* screen = QGuiApplication::primaryScreen()) {
        const QRect area = screen->availableGeometry();
        const QRect frame = m_window->frameGeometry();
        m_window->move(area.center().x() - frame.width() / 2,
                       area.center().y() - frame.height() / 2);
    }""", "show 后居中")

rep("""    QAction* openLog = m_menu->addAction(QStringLiteral("打开日志"));""",
    """    QAction* showPanel = m_menu->addAction(QStringLiteral("显示控制面板"));
    connect(showPanel, &QAction::triggered, this, [this]() {
        if (m_window) {
            m_window->show();
            m_window->raise();
            m_window->activateWindow();
        }
    });

    QAction* openLog = m_menu->addAction(QStringLiteral("打开日志"));""", "托盘入口")

rep('#include <QJsonDocument>', '#include <QGuiApplication>\n#include <QJsonDocument>\n#include <QScreen>', "include screen")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("patched")
