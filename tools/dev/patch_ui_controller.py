# -*- coding: utf-8 -*-
"""阶段 B：AppController 接入 MainWindow、角色绑定、启动器。"""

import io, re, sys

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()


def rep(old, new, label, count=1):
    global t
    if old not in t:
        print(f"[MISS] {label}")
        sys.exit(1)
    t = t.replace(old, new, count)
    print(f"[OK] {label}")


rep('#include "ui/ControlWindow.h"', '#include "ui/MainWindow.h"', "include MainWindow")
rep('#include <QGuiApplication>', '#include <QDesktopServices>\n#include <QDir>\n#include <QFile>\n#include <QGuiApplication>', "includes")
rep('#include <QScreen>', '#include <QProcess>\n#include <QRegularExpression>\n#include <QScreen>', "includes2")

# 1) 替换窗口创建块
start_marker = "    // 控制窗口：双击可看到完整状态（托盘图标可能被 Windows 折叠）"
i = t.find(start_marker)
if i < 0:
    print("[MISS] 窗口创建块")
    sys.exit(1)
j = t.find("    return true;\n}", i)
if j < 0:
    print("[MISS] 窗口创建块结尾")
    sys.exit(1)
new_block = """    m_window = std::make_unique<MainWindow>(this);
    m_window->show();

    auto* statusTimer = new QTimer(this);
    statusTimer->setInterval(2000);
    connect(statusTimer, &QTimer::timeout, this, [this]() { notifyUi(); });
    statusTimer->start();

    Log::info(QStringLiteral("主窗口已显示"));
"""
t = t[:i] + new_block + t[j:]

# 2) 删除旧的 updateWindowStatus 定义
i2 = t.find("void AppController::updateWindowStatus()")
if i2 >= 0:
    j2 = t.find("\n}\n", i2)
    t = t[:i2] + t[j2 + 3:]
    print("[OK] 删除 updateWindowStatus")

# 3) 角色识别：放在 handleChatStream 解析 root 之后
rep("""    const QJsonObject root = doc.object();
    if (!root.value(QStringLiteral("stream")).toBool(false)) {""",
"""    const QJsonObject root = doc.object();

    // 记录本条回复应该用的声线（按角色绑定）
    m_pendingProfile = detectCharacterProfile(request.body);

    if (!root.value(QStringLiteral("stream")).toBool(false)) {""",
"角色识别")

# 4) onAssistantText / pumpSpeech 使用 m_pendingProfile


rep("""    Log::info(QStringLiteral("准备朗读 %1 句").arg(sentences.size()));""",
"""    Log::info(QStringLiteral("准备朗读 %1 句（声线 %2）").arg(sentences.size()).arg(m_pendingProfile.isEmpty() ? m_activeProfile : m_pendingProfile));""",
"朗读日志")

rep("""    const VoiceProfile profile = m_tts->profile(m_activeProfile);""",
"""    const QString profileId = m_pendingProfile.isEmpty() ? m_activeProfile : m_pendingProfile;
    const VoiceProfile profile = m_tts->profile(profileId);""",
"按角色选声线")

# 5) 追加新方法
extra = r'''

/* --------------------------- 角色 / 启动器 --------------------------- */

QString AppController::effectiveCharactersDir() const
{
    if (!m_config.charactersDir.trimmed().isEmpty()) {
        return m_config.charactersDir.trimmed();
    }
    return m_config.launcher.stPath + QStringLiteral("/data/default-user/characters");
}

QStringList AppController::listCharacters() const
{
    QStringList names;
    const QDir dir(effectiveCharactersDir());
    if (!dir.exists()) {
        return names;
    }
    const QStringList filters{QStringLiteral("*.png"), QStringLiteral("*.json"), QStringLiteral("*.webp")};
    for (const QFileInfo& info : dir.entryInfoList(filters, QDir::Files)) {
        names.append(info.completeBaseName());
    }
    names.removeDuplicates();
    names.sort(Qt::CaseInsensitive);
    return names;
}

void AppController::setCharacterVoice(const QString& character, const QString& profileId)
{
    if (character.isEmpty()) {
        return;
    }
    if (profileId.isEmpty()) {
        m_config.characterVoices.remove(character);
    } else {
        m_config.characterVoices.insert(character, profileId);
    }
    saveConfig();
    Log::info(QStringLiteral("角色声线：%1 -> %2").arg(character, profileId.isEmpty() ? QStringLiteral("（默认）") : profileId));
}

void AppController::setDefaultProfile(const QString& profileId)
{
    m_activeProfile = profileId;
    m_config.voice.profile = profileId;
    saveConfig();
    notifyUi();
}

QString AppController::detectCharacterProfile(const QByteArray& body) const
{
    if (m_config.characterVoices.isEmpty()) {
        return QString();
    }
    const QString haystack = QString::fromUtf8(body);
    QString bestName;
    QString bestProfile;
    for (auto it = m_config.characterVoices.constBegin(); it != m_config.characterVoices.constEnd(); ++it) {
        if (it.key().isEmpty() || it.value().isEmpty()) {
            continue;
        }
        if (haystack.contains(it.key()) && it.key().length() > bestName.length()) {
            bestName = it.key();
            bestProfile = it.value();
        }
    }
    if (!bestProfile.isEmpty()) {
        Log::info(QStringLiteral("识别到角色 %1，使用声线 %2").arg(bestName, bestProfile));
    }
    return bestProfile;
}

void AppController::testVoice(const QString& profileId)
{
    if (!m_tts) {
        return;
    }
    const VoiceProfile profile = m_tts->profile(profileId);
    const QString text = QStringLiteral("你好，我是%1。").arg(profile.name.isEmpty() ? profile.id : profile.name);
    Log::info(QStringLiteral("试听声线：%1").arg(profile.id));
    m_tts->ensureWeights(profile, [this, text, profile](const QString& weightError) {
        if (!weightError.isEmpty()) {
            Log::warn(QStringLiteral("试听失败：%1").arg(weightError));
            return;
        }
        m_tts->synthesize(text, QStringLiteral("zh"), profile, m_config.voice.speed,
                          [this](const QByteArray& wav, const QString& error) {
                              if (!error.isEmpty()) {
                                  Log::warn(QStringLiteral("试听合成失败：%1").arg(error));
                                  return;
                              }
                              if (m_audio) {
                                  m_audio->playWav(wav);
                              }
                          });
    });
}

void AppController::saveConfig()
{
    m_config.save(m_config.filePath);
    notifyUi();
}

void AppController::notifyUi()
{
    emit uiDirty();
}

bool AppController::portOpen(quint16 port)
{
    QTcpSocket socket;
    socket.connectToHost(QStringLiteral("127.0.0.1"), port);
    const bool ok = socket.waitForConnected(300);
    socket.abort();
    return ok;
}

namespace {
/** 找监听指定端口的进程 pid（netstat 解析） */
qint64 pidOnPort(quint16 port)
{
    QProcess process;
    process.start(QStringLiteral("netstat"), {QStringLiteral("-ano"), QStringLiteral("-p"), QStringLiteral("tcp")});
    if (!process.waitForFinished(3000)) {
        return 0;
    }
    const QString output = QString::fromLocal8Bit(process.readAllStandardOutput());
    const QString needle = QStringLiteral(":%1").arg(port);
    for (const QString& line : output.split(QLatin1Char('\n'))) {
        if (!line.contains(needle, Qt::CaseInsensitive) || !line.contains(QStringLiteral("LISTENING"), Qt::CaseInsensitive)) {
            continue;
        }
        const QStringList parts = line.trimmed().split(QRegularExpression(QStringLiteral("\\s+")), Qt::SkipEmptyParts);
        if (parts.size() >= 5) {
            return parts.last().toLongLong();
        }
    }
    return 0;
}

bool killPid(qint64 pid, QString* error)
{
    if (pid <= 0) {
        return false;
    }
    QProcess process;
    process.start(QStringLiteral("taskkill"), {QStringLiteral("/PID"), QString::number(pid), QStringLiteral("/F")});
    process.waitForFinished(5000);
    if (process.exitCode() != 0) {
        if (error) {
            *error = QString::fromLocal8Bit(process.readAllStandardError()).trimmed();
        }
        return false;
    }
    return true;
}
} // namespace

bool AppController::startSillyTavern(QString* error)
{
    const QString dir = m_config.launcher.stPath;
    const QString bat = dir + QStringLiteral("/Start.bat");
    if (!QFile::exists(bat)) {
        if (error) {
            *error = QStringLiteral("找不到 %1").arg(bat);
        }
        return false;
    }
    const bool ok = QProcess::startDetached(QStringLiteral("cmd.exe"),
                                            {QStringLiteral("/c"), QStringLiteral("start"), QString(), bat},
                                            dir);
    Log::info(QStringLiteral("启动酒馆：%1（%2）").arg(bat).arg(ok ? QStringLiteral("已拉起") : QStringLiteral("失败")));
    if (!ok && error) {
        *error = QStringLiteral("启动失败，请检查路径");
    }
    return ok;
}

bool AppController::stopSillyTavern(QString* error)
{
    const qint64 pid = pidOnPort(static_cast<quint16>(m_config.launcher.stPort));
    if (pid == 0) {
        if (error) {
            *error = QStringLiteral("酒馆没有在运行（端口 %1 未监听）").arg(m_config.launcher.stPort);
        }
        return false;
    }
    const bool ok = killPid(pid, error);
    Log::info(QStringLiteral("停止酒馆：pid=%1 %2").arg(pid).arg(ok ? QStringLiteral("成功") : QStringLiteral("失败")));
    return ok;
}

bool AppController::startVoiceService(QString* error)
{
    const QString dir = m_config.launcher.gsvPath;
    const QString bat = dir + QStringLiteral("/start-api-v2pro.bat");
    if (!QFile::exists(bat)) {
        if (error) {
            *error = QStringLiteral("找不到 %1").arg(bat);
        }
        return false;
    }
    const bool ok = QProcess::startDetached(QStringLiteral("cmd.exe"),
                                            {QStringLiteral("/c"), QStringLiteral("start"), QString(), bat},
                                            dir);
    Log::info(QStringLiteral("启动语音服务：%1（%2）").arg(bat).arg(ok ? QStringLiteral("已拉起") : QStringLiteral("失败")));
    if (!ok && error) {
        *error = QStringLiteral("启动失败，请检查路径");
    }
    return ok;
}

bool AppController::stopVoiceService(QString* error)
{
    const qint64 pid = pidOnPort(static_cast<quint16>(9880));
    if (pid == 0) {
        if (error) {
            *error = QStringLiteral("语音服务没有在运行（9880 未监听）");
        }
        return false;
    }
    const bool ok = killPid(pid, error);
    Log::info(QStringLiteral("停止语音服务：pid=%1 %2").arg(pid).arg(ok ? QStringLiteral("成功") : QStringLiteral("失败")));
    return ok;
}
'''

if "AppController::detectCharacterProfile" not in t:
    t += extra
    print("[OK] 追加新方法")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("phase B done")
