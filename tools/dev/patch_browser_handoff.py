# -*- coding: utf-8 -*-
"""先让 Start.bat 自己开浏览器；3 秒内没开，我们再兜底开。"""

import io, sys

H = r"E:\dshwork\Demon\src\ui\MainWindow.h"
C = r"E:\dshwork\Demon\src\ui\MainWindow.cpp"
A_H = r"E:\dshwork\Demon\src\app\AppController.h"
A_C = r"E:\dshwork\Demon\src\app\AppController.cpp"

# 1) AppController：浏览器进程计数
h = io.open(A_H, encoding="utf-8").read()
if "browserProcessCount" not in h:
    h = h.replace("    /** 用系统默认浏览器打开 URL（cmd start 优先，失败回退 QDesktopServices） */\n    bool openExternalUrl(const QString& url);",
                  "    /** 用系统默认浏览器打开 URL（cmd start 优先，失败回退 QDesktopServices） */\n    bool openExternalUrl(const QString& url);\n\n    /** 当前在跑的浏览器进程数量（用于判断 ST 是否已经自己打开了浏览器） */\n    static int browserProcessCount();")
    io.open(A_H, "w", encoding="utf-8", newline="").write(h)
    print("[OK] header")

c = io.open(A_C, encoding="utf-8").read()
if "AppController::browserProcessCount" not in c:
    anchor = "bool AppController::openExternalUrl(const QString& url)"
    add = r'''int AppController::browserProcessCount()
{
    QProcess list;
    list.start(QStringLiteral("tasklist"));
    if (!list.waitForFinished(4000)) {
        return -1;
    }
    const QString out = QString::fromLocal8Bit(list.readAllStandardOutput()).toLower();
    const QStringList names{
        QStringLiteral("msedge.exe"), QStringLiteral("chrome.exe"), QStringLiteral("firefox.exe"),
        QStringLiteral("brave.exe"), QStringLiteral("vivaldi.exe"), QStringLiteral("opera.exe"),
        QStringLiteral("360se.exe"), QStringLiteral("360chrome.exe"), QStringLiteral("qqbrowser.exe")
    };
    int count = 0;
    for (const QString& name : names) {
        count += out.count(name);
    }
    return count;
}

'''
    c = c.replace(anchor, add + anchor, 1)
    io.open(A_C, "w", encoding="utf-8", newline="").write(c)
    print("[OK] controller")

# 2) MainWindow：记录启动前浏览器数量，就绪后再等 2.5 秒判断
mh = io.open(H, encoding="utf-8").read()
if "m_browserCountBefore" not in mh:
    mh = mh.replace("    int m_openTries = 0;", "    int m_openTries = 0;\n    int m_browserCountBefore = -1;")
    io.open(H, "w", encoding="utf-8", newline="").write(mh)
    print("[OK] MainWindow.h")

mc = io.open(C, encoding="utf-8").read()
old = r'''        if (AppController::portOpen(port)) {
            m_openTimer->stop();
            const QUrl url(QStringLiteral("http://127.0.0.1:%1/").arg(port));
            openInBrowser(m_controller, url.toString());
            Log::info(QStringLiteral("酒馆已就绪，尝试打开浏览器：%1").arg(url.toString()));
            return;
        }'''
new = r'''        if (AppController::portOpen(port)) {
            m_openTimer->stop();
            // 先给 Start.bat 自己开的浏览器 2.5 秒时间；它没开我们再兜底
            QTimer::singleShot(2500, this, [this, port]() {
                const int now = AppController::browserProcessCount();
                const bool stOpened = (m_browserCountBefore >= 0 && now > m_browserCountBefore);
                const QString url = QStringLiteral("http://127.0.0.1:%1/").arg(port);
                if (stOpened) {
                    Log::info(QStringLiteral("Start.bat 已自行打开浏览器，跳过兜底"));
                    return;
                }
                openInBrowser(m_controller, url);
                Log::info(QStringLiteral("酒馆已就绪，兜底打开浏览器：%1").arg(url));
            });
            return;
        }'''
if old in mc:
    mc = mc.replace(old, new, 1)
    print("[OK] 就绪后延迟判断")
else:
    print("[warn] 就绪块锚点未命中")

old2 = r'''        if (AppController::portOpen(static_cast<quint16>(m_stPort->value()))) {'''
new2 = r'''        m_browserCountBefore = AppController::browserProcessCount();
        if (AppController::portOpen(static_cast<quint16>(m_stPort->value()))) {'''
if old2 in mc:
    mc = mc.replace(old2, new2, 1)
    print("[OK] 启动前记录浏览器数量")
else:
    print("[warn] 启动按钮锚点未命中")

io.open(C, "w", encoding="utf-8", newline="").write(mc)
print("done")
