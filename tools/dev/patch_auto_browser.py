# -*- coding: utf-8 -*-
"""启动酒馆后自动打开浏览器（轮询端口，就绪即打开）。"""

import io, sys

H = r"E:\dshwork\Demon\src\ui\MainWindow.h"
C = r"E:\dshwork\Demon\src\ui\MainWindow.cpp"

h = io.open(H, encoding="utf-8").read()
if "m_openTimer" not in h:
    h = h.replace("    QTimer* m_timer = nullptr;",
                  "    QTimer* m_timer = nullptr;\n    QTimer* m_openTimer = nullptr;\n    int m_openTries = 0;")
    io.open(H, "w", encoding="utf-8", newline="").write(h)
    print("[OK] header")

t = io.open(C, encoding="utf-8").read()


def rep(old, new, label):
    global t
    if old not in t:
        print(f"[MISS] {label}")
        sys.exit(1)
    t = t.replace(old, new, 1)
    print(f"[OK] {label}")


rep("""    m_timer->start();""",
"""    m_timer->start();

    // 启动酒馆后：轮询端口，就绪即自动打开浏览器
    m_openTimer = new QTimer(this);
    m_openTimer->setInterval(600);
    connect(m_openTimer, &QTimer::timeout, this, [this]() {
        ++m_openTries;
        const quint16 port = static_cast<quint16>(m_stPort->value());
        if (AppController::portOpen(port)) {
            m_openTimer->stop();
            const QUrl url(QStringLiteral("http://127.0.0.1:%1/").arg(port));
            QDesktopServices::openUrl(url);
            Log::info(QStringLiteral("酒馆已就绪，已打开浏览器：%1").arg(url.toString()));
            return;
        }
        if (m_openTries > 120) {  // 约 72 秒还没起来就不再等
            m_openTimer->stop();
            Log::warn(QStringLiteral("等待酒馆启动超时（端口 %1 仍未监听）").arg(port));
        }
    });""",
    "自动打开定时器")

rep("""        QString error;
        if (!m_controller->startSillyTavern(&error)) {
            QMessageBox::warning(this, QStringLiteral("启动酒馆"), error);
        }""",
"""        QString error;
        if (!m_controller->startSillyTavern(&error)) {
            QMessageBox::warning(this, QStringLiteral("启动酒馆"), error);
            return;
        }
        if (AppController::portOpen(static_cast<quint16>(m_stPort->value()))) {
            // 已经在跑：直接打开页面
            QDesktopServices::openUrl(QUrl(QStringLiteral("http://127.0.0.1:%1/").arg(m_stPort->value())));
            Log::info(QStringLiteral("酒馆已在运行，直接打开页面"));
        } else {
            m_openTries = 0;
            m_openTimer->start();
            Log::info(QStringLiteral("已启动酒馆，等待端口就绪后自动打开浏览器"));
        }""",
    "启动按钮逻辑")

io.open(C, "w", encoding="utf-8", newline="").write(t)
print("done")
