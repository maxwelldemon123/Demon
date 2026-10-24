#pragma once

#include "config/Config.h"
#include "http/HttpServer.h"

#include <QMap>
#include <QObject>
#include <QStringList>
#include <QSystemTrayIcon>

#include <memory>

class QAction;
class QMenu;
class QActionGroup;
class QNetworkAccessManager;
class QSharedMemory;
class TtsClient;
class MainWindow;
class AudioPlayer;

/**
 * 应用控制器：
 *   - HTTP 兼容端点（/v1/*）
 *   - 语音合成与播放（/voice/*）
 *   - 启动器（酒馆 / GPT-SoVITS）
 *   - 角色声线绑定
 */
class AppController : public QObject {
    Q_OBJECT

public:
    explicit AppController(QObject* parent = nullptr);
    ~AppController() override;

    bool start();

    /** 收到完整回复文本（流式结束后调用），按配置触发语音 */
    void onAssistantText(const QString& text);

    // ---- 供 UI 调用 ----
    const Config& config() const { return m_config; }
    Config& mutableConfig() { return m_config; }
    void saveConfig();

    void applyProfile(const QString& id);
    void applyAutoPlay(bool on);
    void openLogFile();
    void openConfigFolder();
    void reloadConfig();

    /** 扫描角色卡目录，返回角色名 */
    QStringList listCharacters() const;
    QString effectiveCharactersDir() const;
    void setCharacterVoice(const QString& character, const QString& profileId);
    void setDefaultProfile(const QString& profileId);

    /** 立即试听某条声线（不影响朗读队列） */
    void testVoice(const QString& profileId);

    /** 启动器 */
    bool startSillyTavern(QString* error = nullptr);
    bool stopSillyTavern(QString* error = nullptr);
    bool startVoiceService(QString* error = nullptr);
    bool stopVoiceService(QString* error = nullptr);

    static bool portOpen(quint16 port);

    /** 用系统默认浏览器打开 URL（cmd start 优先，失败回退 QDesktopServices） */
    bool openExternalUrl(const QString& url);

    /** 当前在跑的浏览器进程数量（用于判断 ST 是否已经自己打开了浏览器） */
    static int browserProcessCount();

    /** 优先用 Edge 打开 URL（找不到 Edge 再走默认浏览器） */
    bool openInEdge(const QString& url);

    /** UI 刷新用：当前状态摘要 */
    void notifyUi();

signals:
    void uiDirty();

private:
    HttpResponse handleRequest(const HttpRequest& request);
    HttpResponse handleHealthz(const HttpRequest& request);
    HttpResponse handleModels(const HttpRequest& request);
    HttpResponse handleChatCompletions(const HttpRequest& request);
    HttpResponse handleVoiceStatus(const HttpRequest& request);
    bool handleVoiceSpeak(const HttpRequest& request, const std::shared_ptr<HttpStream>& stream);

    /** 流式接管；返回 true 表示已接管连接 */
    bool handleChatStream(const HttpRequest& request, const std::shared_ptr<HttpStream>& stream);

    const UpstreamConfig* pickUpstream(const QString& modelFromRequest) const;
    QByteArray rewriteModel(const QByteArray& body, const QString& upstreamModel) const;

    /** 语音队列：把句子依次合成并播放 */
    void enqueueSpeech(const QStringList& sentences);
    void pumpSpeech();
    void setupVoice();

    /** 从请求体里认出角色，返回绑定的声线 id（没有则空） */
    QString detectCharacterProfile(const QByteArray& body) const;

    void setupTray();
    void showStatus();

    Config m_config;
    std::unique_ptr<HttpServer> m_server;
    std::unique_ptr<QNetworkAccessManager> m_net;
    std::unique_ptr<TtsClient> m_tts;
    std::unique_ptr<AudioPlayer> m_audio;
    QSystemTrayIcon* m_tray = nullptr;
    QMenu* m_menu = nullptr;
    QAction* m_statusAction = nullptr;
    QMenu* m_voiceMenu = nullptr;
    QActionGroup* m_profileGroup = nullptr;
    QAction* m_autoPlayAction = nullptr;
    qint64 m_startedAtMs = 0;
    QString m_dataDir;
    QSharedMemory* m_instanceLock = nullptr;
    std::unique_ptr<MainWindow> m_window;

    QStringList m_speechQueue;
    bool m_synthBusy = false;
    QString m_activeProfile;      // 当前默认声线
    QString m_pendingProfile;     // 本条回复应使用的声线（角色绑定）
};
