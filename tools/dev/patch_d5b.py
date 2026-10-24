# -*- coding: utf-8 -*-
"""D5 补丁 2：托盘可见性 + 单实例检测。"""

import io, sys

ROOT = r"E:\dshwork\Demon"
P = f"{ROOT}\\src\\app\\AppController.cpp"
H = f"{ROOT}\\src\\app\\AppController.h"

h = io.open(H, encoding="utf-8").read()
h = h.replace("class QNetworkAccessManager;", "class QNetworkAccessManager;\nclass QSharedMemory;")
h = h.replace("    QString m_dataDir;", "    QString m_dataDir;\n    QSharedMemory* m_instanceLock = nullptr;")
io.open(H, "w", encoding="utf-8", newline="").write(h)
print("[OK] header")

t = io.open(P, encoding="utf-8").read()


def rep(old, new, label):
    global t
    if old not in t:
        print(f"[MISS] {label}")
        sys.exit(1)
    t = t.replace(old, new, 1)
    print(f"[OK] {label}")


rep("#include <QMessageBox>", "#include <QMessageBox>\n#include <QSharedMemory>", "include QSharedMemory")

# 单实例：抢共享内存
rep("""    m_config = Config::load(exeDir + QStringLiteral("/config.json"));""",
    """    // 单实例：避免用户重复双击导致“端口被占用”的困惑
    m_instanceLock = new QSharedMemory(QStringLiteral("DemonEngineInstance-v1"), this);
    if (!m_instanceLock->create(1)) {
        Log::warn(QStringLiteral("已有实例在运行，本次启动退出"));
        QMessageBox::information(
            nullptr, QStringLiteral("Demon"),
            QStringLiteral("Demon 已经在运行了。\\n\\n"
                           "如果没看到图标，请点任务栏右下角的 ^ 展开隐藏图标，\\n"
                           "里面应该有一个紫色的 D。"));
        return false;
    }

    m_config = Config::load(exeDir + QStringLiteral("/config.json"));""", "单实例锁")

# 托盘可用性日志 + 启动气泡
rep("""    m_tray->show();

    Log::info(QStringLiteral("托盘已创建"));""",
    """    m_tray->show();
    m_tray->showMessage(
        QStringLiteral("Demon 已启动"),
        QStringLiteral("右键托盘里的 D 图标：切换声线 / 开关朗读 / 看日志。\\n"
                       "如果没看到图标，点任务栏右下角的 ^ 展开隐藏图标。"),
        QSystemTrayIcon::Information, 8000);

    Log::info(QStringLiteral("托盘已创建（系统托盘可用=%1，支持气泡=%2）")
                  .arg(QSystemTrayIcon::isSystemTrayAvailable() ? QStringLiteral("是") : QStringLiteral("否"),
                       QSystemTrayIcon::supportsMessages() ? QStringLiteral("是") : QStringLiteral("否")));""",
    "启动气泡")

# 端口占用的文案补充
rep("""        const QString message = QStringLiteral("无法监听 %1:%2，端口可能被占用。\\n\\n"
                                               "请关闭占用该端口的程序，或修改 config.json 里的 listen.port。")""",
    """        const QString message = QStringLiteral("无法监听 %1:%2，端口可能被占用。\\n\\n"
                                               "最常见原因：已经有一个 Demon 在运行（看任务管理器）。\\n"
                                               "或者别的程序占用了这个端口。\\n\\n"
                                               "解决办法：先退出已有的 Demon，或修改 config.json 里的 listen.port。")""",
    "端口文案")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("patch d5b done")
