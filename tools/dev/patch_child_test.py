# -*- coding: utf-8 -*-
"""诊断：CreateProcess 带 BREAKAWAY / 普通模式，看子进程能否存活。"""

import io

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()

anchor = '    if (request.path == QStringLiteral("/launcher/open")) {'
block = r'''    if (request.path == QStringLiteral("/debug/child")) {
        STARTUPINFOW si{};
        si.cb = sizeof(si);
        PROCESS_INFORMATION pi{};
        std::wstring cmd = L"cmd.exe /c timeout 25";
        const BOOL ok = CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, FALSE,
                                       CREATE_NEW_PROCESS_GROUP, nullptr, nullptr, &si, &pi);
        const DWORD err = ok ? 0 : GetLastError();

        QProcess list;
        list.start(QStringLiteral("tasklist"), {QStringLiteral("/FI"), QStringLiteral("IMAGENAME eq timeout.exe")});
        list.waitForFinished(3000);
        const QString tasks = QString::fromLocal8Bit(list.readAllStandardOutput());

        HttpResponse response;
        response.body = QStringLiteral("{\"ok\":%1,\"err\":%2,\"hasTimeout\":%3}")
                            .arg(ok ? QStringLiteral("true") : QStringLiteral("false"))
                            .arg(static_cast<qulonglong>(err))
                            .arg(tasks.contains(QStringLiteral("timeout.exe")) ? QStringLiteral("true") : QStringLiteral("false"))
                            .toUtf8();
        if (ok) {
            CloseHandle(pi.hThread);
            CloseHandle(pi.hProcess);
        }
        return response;
    }
'''
if anchor in t and "/debug/child" not in t:
    t = t.replace(anchor, block + anchor, 1)
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("[OK] debug child endpoint")
else:
    print("[skip] anchor or exists")
