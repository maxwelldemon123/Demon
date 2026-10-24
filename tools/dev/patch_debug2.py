# -*- coding: utf-8 -*-
"""调试接口：用 CreateProcess 起 cmd/notepad/msedge，并检查结果。"""

import io, sys

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()

start = t.find('    if (request.path == QStringLiteral("/debug/spawn")) {')
end = t.find('    if (request.path == QStringLiteral("/launcher/open")) {', start)
if start < 0 or end < 0:
    print("[MISS] debug block")
    sys.exit(1)

new = r'''    if (request.path == QStringLiteral("/debug/spawn")) {
        const QString out = m_dataDir + QStringLiteral("/spawn.txt");
        QFile::remove(out);

        const bool a = spawnCommandLine(QStringLiteral("cmd.exe /c echo hi > ") + out);
        const bool b = spawnCommandLine(QStringLiteral("notepad.exe"));
        const bool c = spawnCommandLine(QStringLiteral("cmd.exe /c start \\"Demon\\" \\"http://127.0.0.1:8000/\\""));

        QThread::msleep(1500);
        QFile check(out);
        const bool fileOk = check.exists();
        HttpResponse response;
        response.body = QStringLiteral("{\"cmdFile\":%1,\"fileExists\":%2,\"notepad\":%3,\"start\":%4}")
                            .arg(a ? QStringLiteral("true") : QStringLiteral("false"),
                                 fileOk ? QStringLiteral("true") : QStringLiteral("false"),
                                 b ? QStringLiteral("true") : QStringLiteral("false"),
                                 c ? QStringLiteral("true") : QStringLiteral("false"))
                            .toUtf8();
        return response;
    }
'''
t = t[:start] + new + t[end:]
if "#include <QThread>" not in t:
    t = t.replace("#include <QTimer>", "#include <QThread>\n#include <QTimer>", 1)
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("[OK] debug spawn rewritten")
