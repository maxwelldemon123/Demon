# -*- coding: utf-8 -*-
"""阶段 A：Config 增加启动器路径、角色声线绑定、角色目录。"""

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


patch("src\\config\\Config.h", [(
"""struct VoiceConfig {""",
"""struct LauncherConfig {
    QString stPath = QStringLiteral("C:\\\\mylove\\\\SillyTavern");
    int stPort = 8000;
    QString gsvPath = QStringLiteral("E:\\\\GPT-SoVITS-v5-20261005\\\\GPT-SoVITS-v2pro-20261006");
};

struct VoiceConfig {""",
"LauncherConfig"),
(
"""    // 其它
    int keepAliveSeconds = 15;""",
"""    // 启动器
    LauncherConfig launcher;

    // 角色声线绑定：角色名 -> 档案 id
    QMap<QString, QString> characterVoices;

    // 角色卡目录（空则用 <stPath>\\data\\default-user\\characters）
    QString charactersDir;

    // 其它
    int keepAliveSeconds = 15;""",
"配置字段"),
])

patch("src\\config\\Config.cpp", [
(
"""    const QJsonObject engine = root.value(QStringLiteral("engine")).toObject();""",
"""    const QJsonObject launcher = root.value(QStringLiteral("launcher")).toObject();
    if (!launcher.isEmpty()) {
        cfg.launcher.stPath = launcher.value(QStringLiteral("stPath")).toString(cfg.launcher.stPath);
        cfg.launcher.stPort = launcher.value(QStringLiteral("stPort")).toInt(cfg.launcher.stPort);
        cfg.launcher.gsvPath = launcher.value(QStringLiteral("gsvPath")).toString(cfg.launcher.gsvPath);
    }

    cfg.charactersDir = root.value(QStringLiteral("charactersDir")).toString();

    const QJsonObject charVoices = root.value(QStringLiteral("characterVoices")).toObject();
    for (auto it = charVoices.constBegin(); it != charVoices.constEnd(); ++it) {
        cfg.characterVoices.insert(it.key(), it.value().toString());
    }

    const QJsonObject engine = root.value(QStringLiteral("engine")).toObject();""",
"解析启动器与绑定"),
(
"""    QJsonObject engine;
    engine.insert(QStringLiteral("keepAliveSeconds"), keepAliveSeconds);""",
"""    QJsonObject launcherOut;
    launcherOut.insert(QStringLiteral("stPath"), launcher.stPath);
    launcherOut.insert(QStringLiteral("stPort"), launcher.stPort);
    launcherOut.insert(QStringLiteral("gsvPath"), launcher.gsvPath);
    root.insert(QStringLiteral("launcher"), launcherOut);

    root.insert(QStringLiteral("charactersDir"), charactersDir);

    QJsonObject charVoicesOut;
    for (auto it = characterVoices.constBegin(); it != characterVoices.constEnd(); ++it) {
        charVoicesOut.insert(it.key(), it.value());
    }
    root.insert(QStringLiteral("characterVoices"), charVoicesOut);

    QJsonObject engine;
    engine.insert(QStringLiteral("keepAliveSeconds"), keepAliveSeconds);""",
"序列化启动器与绑定"),
])

print("config patched")
