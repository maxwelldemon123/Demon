# -*- coding: utf-8 -*-
"""A 方案：Edge --app 模式（独立无地址栏窗口，零体积）。"""

import io

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()

start = t.find("bool AppController::openInEdge(const QString& url)")
end = t.find("\n}\n", start)
if start < 0 or end < 0:
    print("[MISS] openInEdge")
    raise SystemExit(1)

new = r'''bool AppController::openInEdge(const QString& url)
{
    const QStringList candidates{
        QStringLiteral("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        QStringLiteral("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    };
    for (const QString& exe : candidates) {
        if (!QFile::exists(exe)) {
            continue;
        }
        // --app 模式：独立窗口、无地址栏、无标签页，看起来像内置浏览器
        const QString line = QStringLiteral("cmd.exe /c start \"\" \"%1\" --app=%2").arg(exe, url);
        if (spawnCommandLine(line)) {
            Log::info(QStringLiteral("已用 Edge --app 打开：%1").arg(url));
            return true;
        }
    }
    Log::warn(QStringLiteral("没找到 Edge，回退默认浏览器"));
    return openExternalUrl(url);
}
'''

t = t[:start] + new + t[end + 3:]
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("[OK] --app 模式")
