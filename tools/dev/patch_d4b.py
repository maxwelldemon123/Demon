# -*- coding: utf-8 -*-
"""D4 补丁（第二段）：AppController.cpp 的保活、路由、托盘声线菜单、音量。"""

import io, sys

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
text = io.open(P, encoding="utf-8").read()


def rep(old, new, label):
    global text
    if old not in text:
        print(f"[MISS] {label}")
        sys.exit(1)
    text = text.replace(old, new, 1)
    print(f"[OK] {label}")


# 1) include QActionGroup
rep('#include <QAction>', '#include <QAction>\n#include <QActionGroup>', "include QActionGroup")

# 2) StreamJob 增加保活定时器
rep("""    StreamJob(QNetworkReply* reply, const std::shared_ptr<HttpStream>& stream, QObject* owner,
              std::function<void(const QString&)> onText)""",
    """    StreamJob(QNetworkReply* reply, const std::shared_ptr<HttpStream>& stream, QObject* owner,
              std::function<void(const QString&)> onText, int keepAliveMs)""", "构造签名加 keepAliveMs")

rep("""        Log::info(QStringLiteral("流式任务已创建"));
    }""",
    """        if (keepAliveMs > 0) {
            m_keepAlive = new QTimer(this);
            m_keepAlive->setInterval(keepAliveMs);
            QObject::connect(m_keepAlive, &QTimer::timeout, this, [this]() {
                if (m_stream) {
                    m_stream->writeChunk(":keep-alive\\n\\n");
                }
            });
            m_keepAlive->start();
        }

        Log::info(QStringLiteral("流式任务已创建（保活 %1 ms）").arg(keepAliveMs));
    }""", "启动保活定时器")

rep("""        Log::info(QStringLiteral("流式结束，共转发 %1 字节，文本 %2 字").arg(m_received).arg(m_text.size()));""",
    """        if (m_keepAlive) {
            m_keepAlive->stop();
        }
        Log::info(QStringLiteral("流式结束，共转发 %1 字节，文本 %2 字").arg(m_received).arg(m_text.size()));""",
    "结束时停保活")

rep("""    QPointer<QNetworkReply> m_reply;""",
    """    QTimer* m_keepAlive = nullptr;
    QPointer<QNetworkReply> m_reply;""", "保活成员")

# 3) 创建时传间隔
rep("""    new StreamJob(reply, stream, this, [this](const QString& text) {
        Log::info(QStringLiteral("回调：收到完整文本 %1 字").arg(text.size()));
        onAssistantText(text);
    });""",
    """    new StreamJob(reply, stream, this, [this](const QString& text) {
        Log::info(QStringLiteral("回调：收到完整文本 %1 字").arg(text.size()));
        onAssistantText(text);
    }, m_config.keepAliveSeconds * 1000);""", "传保活间隔")

# 4) 声线音量
rep("""    m_audio = std::make_unique<AudioPlayer>();""",
    """    m_audio = std::make_unique<AudioPlayer>();
    m_audio->setVolume(m_config.voice.volume);""", "应用音量")

# 5) 上游按模型名路由
rep("""const UpstreamConfig* AppController::pickUpstream(const QString& modelFromRequest) const
{
    Q_UNUSED(modelFromRequest);
    const QString id = m_config.effectiveUpstreamId();""",
    """const UpstreamConfig* AppController::pickUpstream(const QString& modelFromRequest) const
{
    // 请求里的 model 若是某个上游的 id 或上游模型名，就路由到它；否则用默认
    if (!modelFromRequest.isEmpty()) {
        for (const UpstreamConfig& u : m_config.upstreams) {
            if (u.id == modelFromRequest || u.model == modelFromRequest) {
                return &u;
            }
        }
    }

    const QString id = m_config.effectiveUpstreamId();""", "按模型名路由")

# 6) 托盘：声线子菜单 + 自动朗读开关
rep("""    m_menu->addSeparator();

    QAction* openLog = m_menu->addAction(QStringLiteral("打开日志"));""",
    """    m_voiceMenu = m_menu->addMenu(QStringLiteral("声线"));
    m_profileGroup = new QActionGroup(this);
    m_profileGroup->setExclusive(true);
    for (const VoiceProfileConfig& profile : m_config.voiceProfiles) {
        QAction* action = m_voiceMenu->addAction(profile.id);
        action->setCheckable(true);
        action->setChecked(profile.id == m_activeProfile);
        m_profileGroup->addAction(action);
        const QString id = profile.id;
        connect(action, &QAction::triggered, this, [this, id]() {
            m_activeProfile = id;
            m_config.voice.profile = id;
            m_config.save(m_config.filePath);
            Log::info(QStringLiteral("声线切换为 %1").arg(id));
            showStatus();
        });
    }

    m_autoPlayAction = m_menu->addAction(QStringLiteral("自动朗读"));
    m_autoPlayAction->setCheckable(true);
    m_autoPlayAction->setChecked(m_config.voice.autoPlay);
    connect(m_autoPlayAction, &QAction::toggled, this, [this](bool on) {
        m_config.voice.autoPlay = on;
        m_config.save(m_config.filePath);
        Log::info(QStringLiteral("自动朗读已%1").arg(on ? QStringLiteral("开启") : QStringLiteral("关闭")));
    });

    m_menu->addSeparator();

    QAction* openLog = m_menu->addAction(QStringLiteral("打开日志"));""", "托盘声线菜单")

io.open(P, "w", encoding="utf-8", newline="").write(text)
print("patch2 done")
