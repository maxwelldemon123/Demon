# -*- coding: utf-8 -*-
"""扩展诊断：分别启动 notepad 与 msedge，报告是否存活。"""

import io

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()

start = t.find('    if (request.path == QStringLiteral("/debug/child")) {')
end = t.find('    if (request.path == QStringLiteral("/launcher/open")) {', start)
if start < 0 or end < 0:
    print("[MISS]")
    raise SystemExit(1)

block = r'''    if (request.path == QStringLiteral("/debug/child")) {
        auto spawn = [](const std::wstring& cmd) {
            STARTUPINFOW si{};
            si.cb = sizeof(si);
            PROCESS_INFORMATION pi{};
            std::wstring mutableCmd = cmd;
            const BOOL ok = CreateProcessW(nullptr, mutableCmd.data(), nullptr, nullptr, FALSE,
                                           CREATE_NEW_PROCESS_GROUP, nullptr, nullptr, &si, &pi);
            if (ok) {
                CloseHandle(pi.hThread);
                CloseHandle(pi.hProcess);
            }
            return ok;
        };

        const bool np = spawn(L"notepad.exe");
        const QString edge = defaultBrowserExe();
        const bool ms = !edge.isEmpty()
            && spawn(QStringLiteral("\"%1\" \"http://127.0.0.1:8000/\"").arg(edge).toStdWString());

        QThread::msleep(2500);

        QProcess list;
        list.start(QStringLiteral("tasklist"));
        list.waitForFinished(4000);
        const QString tasks = QString::fromLocal8Bit(list.readAllStandardOutput());

        HttpResponse response;
        response.body = QStringLiteral("{\"notepadSpawn\":%1,\"notepadAlive\":%2,\"edgeSpawn\":%3,\"edgeAlive\":%4,\"edgePath\":\"%5\"}")
                            .arg(np ? QStringLiteral("true") : QStringLiteral("false"),
                                 tasks.contains(QStringLiteral("notepad.exe")) ? QStringLiteral("true") : QStringLiteral("false"),
                                 ms ? QStringLiteral("true") : QStringLiteral("false"),
                                 tasks.contains(QStringLiteral("msedge.exe")) ? QStringLiteral("true") : QStringLiteral("false"),
                                 edge)
                            .toUtf8();
        return response;
    }
'''

t = t[:start] + block + t[end:]
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("[OK] debug child extended")
