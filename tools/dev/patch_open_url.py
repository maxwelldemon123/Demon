# -*- coding: utf-8 -*-
"""把打开浏览器抽到 AppController，并加 /launcher/open 接口。"""

import io, sys

ROOT = r"E:\dshwork\Demon"


def patch(path, pairs):
    p = f"{ROOT}\\{path}"
    text = io.open(p, encoding="utf-8").read()
    for old, new, label in pairs:
        if old not in text:
            print(f"[MISS] {path} -> {label}")
            sys.exit(1)
        text = text.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(text)
    print(f"[OK] {path}")


patch("src\\app\\AppController.h", [(
"""    static bool portOpen(quint16 port);""",
"""    static bool portOpen(quint16 port);

    /** 用系统默认浏览器打开 URL（cmd start 优先，失败回退 QDesktopServices） */
    bool openExternalUrl(const QString& url);""",
"声明 openExternalUrl"),
])

patch("src\\app\\AppController.cpp", [
(
"""#include <QDesktopServices>""",
"""#include <QDesktopServices>
#include <QUrl>""",
"include QUrl"),
(
"""bool AppController::portOpen(quint16 port)""",
"""bool AppController::openExternalUrl(const QString& url)
{
    const bool ok = QProcess::startDetached(QStringLiteral("cmd.exe"),
                                            {QStringLiteral("/c"), QStringLiteral("start"), QString(), url});
    if (ok) {
        Log::info(QStringLiteral("已通过 cmd start 打开：%1").arg(url));
        return true;
    }
    Log::warn(QStringLiteral("cmd start 失败，回退 QDesktopServices"));
    const bool fallback = QDesktopServices::openUrl(QUrl(url));
    Log::info(QStringLiteral("QDesktopServices 结果：%1").arg(fallback ? QStringLiteral("成功") : QStringLiteral("失败")));
    return fallback;
}

bool AppController::portOpen(quint16 port)""",
"实现 openExternalUrl"),
(
"""    if (request.path == QStringLiteral("/voice/status")) {""",
"""    if (request.path == QStringLiteral("/launcher/open")) {
        const QString url = QStringLiteral("http://127.0.0.1:%1/").arg(m_config.launcher.stPort);
        openExternalUrl(url);
        HttpResponse response;
        response.body = QStringLiteral("{\\"opened\\":\\"%1\\"}").arg(url).toUtf8();
        return response;
    }
    if (request.path == QStringLiteral("/voice/status")) {""",
"路由 /launcher/open"),
])

# MainWindow 改用 controller 的方法
P = f"{ROOT}\\src\\ui\\MainWindow.cpp"
t = io.open(P, encoding="utf-8").read()
start = t.find("bool openInBrowser(const QUrl& url)")
end = t.find("}", t.find("return QDesktopServices::openUrl(url);", start))
if start >= 0 and end >= 0:
    t = t[:start] + "bool openInBrowser(AppController* controller, const QString& url)\n{\n    return controller->openExternalUrl(url);\n" + t[end + 1:]
    t = t.replace("openInBrowser(url);", "openInBrowser(m_controller, url.toString());")
    t = t.replace("openInBrowser(QUrl(QStringLiteral(\"http://127.0.0.1:%1/\").arg(m_stPort->value())));",
                  "openInBrowser(m_controller, QStringLiteral(\"http://127.0.0.1:%1/\").arg(m_stPort->value()));")
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("[OK] MainWindow 改用 controller")
else:
    print("[warn] openInBrowser 锚点未命中")
