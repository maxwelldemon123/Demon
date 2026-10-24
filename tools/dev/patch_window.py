# -*- coding: utf-8 -*-
"""接入 ControlWindow。"""

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


patch("src\\app\\AppController.h", [
("""class TtsClient;""", """class TtsClient;
class ControlWindow;""", "前向声明"),
("""    /** 收到完整回复文本（流式结束后调用），按配置触发语音 */
    void onAssistantText(const QString& text);""",
"""    /** 收到完整回复文本（流式结束后调用），按配置触发语音 */
    void onAssistantText(const QString& text);

    /** 供控制窗口调用的操作 */
    void applyProfile(const QString& id);
    void applyAutoPlay(bool on);
    void openLogFile();
    void openConfigFolder();
    void reloadConfig();
    void updateWindowStatus();""", "方法声明"),
("""    QSharedMemory* m_instanceLock = nullptr;""",
"""    QSharedMemory* m_instanceLock = nullptr;
    std::unique_ptr<ControlWindow> m_window;""", "窗口成员"),
])

patch("src\\app\\AppController.cpp", [
("""#include "voice/AudioPlayer.h\"""",
"""#include "ui/ControlWindow.h"
#include "voice/AudioPlayer.h\"""", "include 窗口"),
("""    setupTray();
    return true;""",
"""    setupTray();

    // 控制窗口：双击可看到完整状态（托盘图标可能被 Windows 折叠）
    ControlWindow::Callbacks callbacks;
    callbacks.switchProfile = [this](const QString& id) { applyProfile(id); };
    callbacks.setAutoPlay = [this](bool on) { applyAutoPlay(on); };
    callbacks.reloadConfig = [this]() { reloadConfig(); };
    callbacks.openLog = [this]() { openLogFile(); };
    callbacks.openConfigDir = [this]() { openConfigFolder(); };
    callbacks.quit = []() { QCoreApplication::quit(); };

    m_window = std::make_unique<ControlWindow>(callbacks);
    QStringList profileIds;
    for (const VoiceProfileConfig& p : m_config.voiceProfiles) {
        profileIds.append(p.id);
    }
    m_window->setProfiles(profileIds, m_activeProfile);
    updateWindowStatus();
    m_window->show();

    auto* statusTimer = new QTimer(this);
    statusTimer->setInterval(2000);
    connect(statusTimer, &QTimer::timeout, this, [this]() { updateWindowStatus(); });
    statusTimer->start();

    Log::info(QStringLiteral("控制窗口已显示"));
    return true;""", "创建窗口"),
])

# 追加方法实现
P = f"{ROOT}\\src\\app\\AppController.cpp"
text = io.open(P, encoding="utf-8").read()
impl = r'''
/* ---------------------------- 控制窗口操作 ---------------------------- */

void AppController::applyProfile(const QString& id)
{
    m_activeProfile = id;
    m_config.voice.profile = id;
    m_config.save(m_config.filePath);
    Log::info(QStringLiteral("声线切换为 %1").arg(id));
    updateWindowStatus();
}

void AppController::applyAutoPlay(bool on)
{
    m_config.voice.autoPlay = on;
    m_config.save(m_config.filePath);
    Log::info(QStringLiteral("自动朗读已%1").arg(on ? QStringLiteral("开启") : QStringLiteral("关闭")));
    updateWindowStatus();
}

void AppController::openLogFile()
{
    QProcess::startDetached(QStringLiteral("notepad.exe"),
                            {QCoreApplication::applicationDirPath() + QStringLiteral("/data/demon.log")});
}

void AppController::openConfigFolder()
{
    QProcess::startDetached(QStringLiteral("explorer.exe"), {QCoreApplication::applicationDirPath()});
}

void AppController::reloadConfig()
{
    m_config = Config::load(QCoreApplication::applicationDirPath() + QStringLiteral("/config.json"));
    if (m_tts) {
        m_tts->setEndpoint(m_config.voice.endpoint);
        QVector<VoiceProfile> profiles;
        for (const VoiceProfileConfig& p : m_config.voiceProfiles) {
            VoiceProfile vp;
            vp.id = p.id;
            vp.refAudio = p.refAudio;
            vp.promptText = p.promptText;
            vp.promptLang = p.promptLang;
            profiles.append(vp);
        }
        m_tts->setProfiles(profiles);
    }
    m_activeProfile = m_config.voice.profile;
    Log::info(QStringLiteral("配置已重载"));
    updateWindowStatus();
}

void AppController::updateWindowStatus()
{
    if (!m_window) {
        return;
    }
    const UpstreamConfig* upstream = pickUpstream(QString());
    const QString upstreamText = upstream
        ? QStringLiteral("%1（%2）").arg(upstream->baseUrl, upstream->model)
        : QStringLiteral("未配置");
    m_window->updateStatus(QStringLiteral("%1:%2").arg(m_config.host).arg(m_config.port),
                           upstreamText,
                           m_config.modelId,
                           m_activeProfile,
                           m_config.voice.autoPlay,
                           m_config.voiceProfiles.size(),
                           m_speechQueue.size());
}

'''
if "void AppController::applyProfile" not in text:
    text = text.replace("void AppController::setupTray()", impl + "void AppController::setupTray()")
    io.open(P, "w", encoding="utf-8", newline="").write(text)
    print("[OK] 方法实现")

# 托盘双击显示窗口
text = io.open(P, encoding="utf-8").read()
old = """        if (reason == QSystemTrayIcon::Trigger) {
            showStatus();
        }"""
new = """        if (reason == QSystemTrayIcon::Trigger) {
            showStatus();
        } else if (reason == QSystemTrayIcon::DoubleClick && m_window) {
            m_window->show();
            m_window->raise();
            m_window->activateWindow();
        }"""
if old in text:
    text = text.replace(old, new, 1)
    io.open(P, "w", encoding="utf-8", newline="").write(text)
    print("[OK] 托盘双击")
else:
    print("[warn] 托盘双击锚点未命中")

print("patch window done")
