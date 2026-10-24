# -*- coding: utf-8 -*-
"""简化：端口就绪后直接 Edge 打开；去掉浏览器进程计数逻辑。"""

import io, sys

ROOT = r"E:\dshwork\Demon"
A_H = f"{ROOT}\\src\\app\\AppController.h"
A_C = f"{ROOT}\\src\\app\\AppController.cpp"
M_C = f"{ROOT}\\src\\ui\\MainWindow.cpp"
M_H = f"{ROOT}\\src\\ui\\MainWindow.h"

# 1) AppController: openInEdge
h = io.open(A_H, encoding="utf-8").read()
if "openInEdge" not in h:
    h = h.replace("    /** 当前在跑的浏览器进程数量（用于判断 ST 是否已经自己打开了浏览器） */\n    static int browserProcessCount();",
                  "    /** 当前在跑的浏览器进程数量（用于判断 ST 是否已经自己打开了浏览器） */\n    static int browserProcessCount();\n\n    /** 优先用 Edge 打开 URL（找不到 Edge 再走默认浏览器） */\n    bool openInEdge(const QString& url);")
    io.open(A_H, "w", encoding="utf-8", newline="").write(h)
    print("[OK] header")

c = io.open(A_C, encoding="utf-8").read()
if "AppController::openInEdge" not in c:
    anchor = "bool AppController::openExternalUrl(const QString& url)"
    add = r'''bool AppController::openInEdge(const QString& url)
{
    const QStringList candidates{
        QStringLiteral("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        QStringLiteral("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    };
    for (const QString& exe : candidates) {
        if (!QFile::exists(exe)) {
            continue;
        }
        // 用 cmd start 起，避免直接 CreateProcess 时路径空格的坑
        const QString line = QStringLiteral("cmd.exe /c start \"\" \"%1\" \"%2\"").arg(exe, url);
        if (spawnCommandLine(line)) {
            Log::info(QStringLiteral("已用 Edge 打开：%1（%2）").arg(url, exe));
            return true;
        }
    }
    Log::warn(QStringLiteral("没找到 Edge，回退默认浏览器"));
    return openExternalUrl(url);
}

'''
    c = c.replace(anchor, add + anchor, 1)
    io.open(A_C, "w", encoding="utf-8", newline="").write(c)
    print("[OK] openInEdge")

# 2) MainWindow: 去掉计数与 2.5s 延迟，就绪即 Edge 打开
mc = io.open(M_C, encoding="utf-8").read()

old_ready = r'''        if (AppController::portOpen(port)) {
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
new_ready = r'''        if (AppController::portOpen(port)) {
            m_openTimer->stop();
            const QString url = QStringLiteral("http://127.0.0.1:%1/").arg(port);
            m_controller->openInEdge(url);
            Log::info(QStringLiteral("酒馆已就绪，已用 Edge 打开：%1").arg(url));
            return;
        }'''
if old_ready in mc:
    mc = mc.replace(old_ready, new_ready, 1)
    print("[OK] 就绪即开 Edge")
else:
    print("[warn] 就绪块未命中")

old_snap = "        m_browserCountBefore = AppController::browserProcessCount();\n"
if old_snap in mc:
    mc = mc.replace(old_snap, "", 1)
    print("[OK] 移除计数")

old_direct = r'''        if (AppController::portOpen(static_cast<quint16>(m_stPort->value()))) {
            // 已经在跑：直接打开页面
            openInBrowser(m_controller, QStringLiteral("http://127.0.0.1:%1/").arg(m_stPort->value()));
            Log::info(QStringLiteral("酒馆已在运行，直接打开页面"));'''
new_direct = r'''        if (AppController::portOpen(static_cast<quint16>(m_stPort->value()))) {
            // 已经在跑：直接打开页面
            m_controller->openInEdge(QStringLiteral("http://127.0.0.1:%1/").arg(m_stPort->value()));
            Log::info(QStringLiteral("酒馆已在运行，直接用 Edge 打开页面"));'''
if old_direct in mc:
    mc = mc.replace(old_direct, new_direct, 1)
    print("[OK] 已在运行时直接 Edge")

io.open(M_C, "w", encoding="utf-8", newline="").write(mc)
print("done")
