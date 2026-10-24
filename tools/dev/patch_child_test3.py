# -*- coding: utf-8 -*-
"""对比三种打开方式，找出在这台机器上真正有效的。"""

import io

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()

start = t.find('    if (request.path == QStringLiteral("/debug/child")) {')
end = t.find('    if (request.path == QStringLiteral("/launcher/open")) {', start)
if start < 0 or end < 0:
    print("[MISS]")
    raise SystemExit(1)

block = r'''    if (request.path == QStringLiteral("/debug/child")) {
        const QString edge = defaultBrowserExe();
        const QString url = QStringLiteral("http://127.0.0.1:8000/");

        const bool a = spawnCommandLine(QStringLiteral("explorer.exe %1").arg(url));
        QThread::msleep(600);
        const bool b = spawnCommandLine(QStringLiteral("cmd.exe /c start \"\" %1").arg(url));
        QThread::msleep(600);
        const bool c = spawnCommandLine(QStringLiteral("cmd.exe /c start \"\" notepad.exe"));
        QThread::msleep(3000);

        QProcess list;
        list.start(QStringLiteral("tasklist"));
        list.waitForFinished(5000);
        const QString tasks = QString::fromLocal8Bit(list.readAllStandardOutput());

        HttpResponse response;
        response.body = QStringLiteral("{\"explorer\":%1,\"cmdStartUrl\":%2,\"cmdStartNotepad\":%3,\"edgeAlive\":%4,\"notepadAlive\":%5}")
                            .arg(a ? QStringLiteral("true") : QStringLiteral("false"),
                                 b ? QStringLiteral("true") : QStringLiteral("false"),
                                 c ? QStringLiteral("true") : QStringLiteral("false"),
                                 tasks.contains(QStringLiteral("msedge.exe")) ? QStringLiteral("true") : QStringLiteral("false"),
                                 tasks.contains(QStringLiteral("notepad.exe")) ? QStringLiteral("true") : QStringLiteral("false"))
                            .toUtf8();
        return response;
    }
'''

t = t[:start] + block + t[end:]
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("[OK] 三路对比诊断")
