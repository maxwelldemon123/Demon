# -*- coding: utf-8 -*-
"""用 Win32 CreateProcess 打开 URL（绕开 Qt startDetached 的问题）。"""

import io, sys

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()

start = t.find("bool AppController::openExternalUrl(const QString& url)")
end = t.find("\n}\n", start)
if start < 0 or end < 0:
    print("[MISS] openExternalUrl")
    sys.exit(1)

new = r'''namespace {

/** 用 Win32 CreateProcess 启动一条命令行（不依赖 Qt 的 detached 逻辑） */
bool spawnCommandLine(const QString& commandLine)
{
#ifdef Q_OS_WIN
    std::wstring cmd = commandLine.toStdWString();
    STARTUPINFOW si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    const BOOL ok = CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, FALSE,
                                   CREATE_NEW_PROCESS_GROUP | CREATE_UNICODE_ENVIRONMENT,
                                   nullptr, nullptr, &si, &pi);
    if (!ok) {
        Log::warn(QStringLiteral("CreateProcessW 失败，错误码 %1").arg(GetLastError()));
        return false;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return true;
#else
    Q_UNUSED(commandLine);
    return false;
#endif
}

} // namespace

bool AppController::openExternalUrl(const QString& url)
{
    // cmd start 的第一个参数是窗口标题；给个固定标题，避免 URL 被当成标题。
    const QString line = QStringLiteral("cmd.exe /c start \"Demon\" \"%1\"").arg(url);
    if (spawnCommandLine(line)) {
        Log::info(QStringLiteral("已通过 cmd start 打开：%1").arg(url));
        return true;
    }
    const bool ok = QDesktopServices::openUrl(QUrl(url));
    Log::info(QStringLiteral("QDesktopServices 结果：%1").arg(ok ? QStringLiteral("成功") : QStringLiteral("失败")));
    return ok;
}
'''

t = t[:start] + new + t[end + 3:]

if "#include <windows.h>" not in t:
    t = t.replace("#include <QSettings>", "#include <QSettings>\n\n#ifdef Q_OS_WIN\n#include <windows.h>\n#endif", 1)

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("[OK] CreateProcessW 版本已写入")
