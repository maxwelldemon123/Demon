# -*- coding: utf-8 -*-
"""打开浏览器：读默认浏览器命令，直接拉起 exe（绕过 shell 激活）。"""

import io, sys

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()

start = t.find("bool AppController::openExternalUrl(const QString& url)")
end = t.find("\n}\n", start)
if start < 0 or end < 0:
    print("[MISS] openExternalUrl")
    sys.exit(1)

new = r'''namespace {

/** 从注册表读默认浏览器的可执行路径（取命令行的第一个 exe） */
QString defaultBrowserExe()
{
    QString progId;
    {
        QSettings assoc(QStringLiteral("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\http\\UserChoice"),
                        QSettings::NativeFormat);
        progId = assoc.value(QStringLiteral("ProgId")).toString();
    }
    if (progId.isEmpty()) {
        return QString();
    }
    QSettings cmd(QStringLiteral("HKEY_CLASSES_ROOT\\%1\\shell\\open\\command").arg(progId),
                  QSettings::NativeFormat);
    const QString command = cmd.value(QStringLiteral(".")).toString();
    if (command.isEmpty()) {
        return QString();
    }
    // 形如 "C:\...\msedge.exe" --single-argument %1
    QString exe;
    if (command.startsWith(QLatin1Char('"'))) {
        const int closing = command.indexOf(QLatin1Char('"'), 1);
        if (closing > 0) {
            exe = command.mid(1, closing - 1);
        }
    } else {
        exe = command.section(QLatin1Char(' '), 0, 0);
    }
    return QFile::exists(exe) ? exe : QString();
}

} // namespace

bool AppController::openExternalUrl(const QString& url)
{
    // 方案 1：直接拉起默认浏览器 exe（最可靠，绕过 shell 激活）
    const QString browser = defaultBrowserExe();
    if (!browser.isEmpty()) {
        const bool ok = QProcess::startDetached(browser, {url});
        Log::info(QStringLiteral("用默认浏览器 %1 打开 %2：%3")
                      .arg(browser, url, ok ? QStringLiteral("成功") : QStringLiteral("失败")));
        if (ok) {
            return true;
        }
    }

    // 方案 2：rundll32
    if (QProcess::startDetached(QStringLiteral("rundll32.exe"),
                                {QStringLiteral("url.dll,FileProtocolHandler"), url})) {
        Log::info(QStringLiteral("已通过 rundll32 打开：%1").arg(url));
        return true;
    }

    // 方案 3：cmd start
    if (QProcess::startDetached(QStringLiteral("cmd.exe"),
                                {QStringLiteral("/c"), QStringLiteral("start"), QString(), url})) {
        Log::info(QStringLiteral("已通过 cmd start 打开：%1").arg(url));
        return true;
    }

    // 方案 4：Qt
    const bool ok = QDesktopServices::openUrl(QUrl(url));
    Log::info(QStringLiteral("QDesktopServices 结果：%1").arg(ok ? QStringLiteral("成功") : QStringLiteral("失败")));
    return ok;
}
'''

t = t[:start] + new + t[end + 3:]

# 补 include
for inc in ('#include <QSettings>',):
    if inc not in t:
        t = t.replace('#include <QSharedMemory>', inc + '\n#include <QSharedMemory>', 1)

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("[OK] openExternalUrl 改为直接启动浏览器")
