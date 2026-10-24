#include "AppController.h"

#include "util/Log.h"
#include "util/TextSplit.h"
#include "ui/MainWindow.h"
#include "voice/AudioPlayer.h"
#include "voice/TtsClient.h"

#include <QAction>
#include <QActionGroup>
#include <QApplication>
#include <QDateTime>
#include <QDir>
#include <QDesktopServices>
#include <QUrl>
#include <QDir>
#include <QFile>
#include <QGuiApplication>
#include <QJsonDocument>
#include <QProcess>
#include <QRegularExpression>
#include <QScreen>
#include <QMessageBox>
#include <QSettings>

#ifdef Q_OS_WIN
#include <windows.h>
#endif
#include <QSharedMemory>
#include <QJsonObject>
#include <QMenu>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QPainter>
#include <QPixmap>
#include <QProcess>
#include <QJsonArray>
#include <QSystemTrayIcon>
#include <QThread>
#include <QTimer>
#include <QTcpSocket>

namespace {
bool spawnCommandLine(const QString& commandLine);
QString defaultBrowserExe();
} // namespace

namespace {

QByteArray jsonErrorBody(const QString& message)
{
    QJsonObject error;
    error.insert(QStringLiteral("message"), message);
    QJsonObject root;
    root.insert(QStringLiteral("error"), error);
    return QJsonDocument(root).toJson(QJsonDocument::Compact);
}

QByteArray sseData(const QByteArray& payload)
{
    QByteArray out = "data: ";
    out += payload;
    out += "\n\n";
    return out;
}

} // namespace

namespace {

/**
 * 单次流式转发任务。
 *   - parent 设为 reply：reply 销毁时它一起销毁
 *   - 只捕获 this，不捕获外部局部变量
 */
class StreamJob : public QObject {
public:
    StreamJob(QNetworkReply* reply, const std::shared_ptr<HttpStream>& stream, QObject* owner,
              std::function<void(const QString&)> onText, int keepAliveMs)
        : QObject(reply)
        , m_reply(reply)
        , m_stream(stream)
        , m_onText(std::move(onText))
    {
        QObject::connect(reply, &QNetworkReply::readyRead, this, [this]() { onReadyRead(); });
        QObject::connect(reply, &QNetworkReply::finished, this, [this]() { onFinished(); });
        if (m_stream && m_stream->socket) {
            QObject::connect(m_stream->socket, &QTcpSocket::disconnected, this, [this]() { onClientGone(); });
        }
        if (keepAliveMs > 0) {
            m_keepAlive = new QTimer(this);
            m_keepAlive->setInterval(keepAliveMs);
            QObject::connect(m_keepAlive, &QTimer::timeout, this, [this]() {
                if (m_stream) {
                    m_stream->writeChunk(":keep-alive\n\n");
                }
            });
            m_keepAlive->start();
        }

        Log::info(QStringLiteral("流式任务已创建（保活 %1 ms）").arg(keepAliveMs));
    }

private:
    void onReadyRead()
    {
        if (!m_reply) {
            return;
        }
        const QByteArray chunk = m_reply->readAll();
        m_received += chunk.size();
        if (m_stream) {
            m_stream->writeChunk(chunk);
        }
        accumulate(chunk);
    }

    void onFinished()
    {
        if (m_done) {
            return;
        }
        m_done = true;

        if (m_reply && m_reply->error() != QNetworkReply::NoError) {
            // 无论是首包就失败还是中途断开，都要让客户端收到明确的结束标记，
            // 否则酒馆会一直转圈等 token。
            Log::error(QStringLiteral("上游失败：%1（已收到 %2 字节）")
                           .arg(m_reply->errorString())
                           .arg(m_received));
            if (m_stream) {
                const QByteArray payload = QStringLiteral(
                    "{\"error\":{\"message\":\"上游中断：%1\"}}")
                                               .arg(m_reply->errorString())
                                               .toUtf8();
                m_stream->writeChunk("data: " + payload + "\n\n");
                m_stream->writeChunk("data: [DONE]\n\n");
            }
        } else if (m_received == 0 && m_stream) {
            m_stream->writeChunk("data: [DONE]\n\n");
        }

        if (m_onText && !m_text.isEmpty()) {
            m_onText(m_text);
        }

        if (m_keepAlive) {
            m_keepAlive->stop();
        }
        Log::info(QStringLiteral("流式结束，共转发 %1 字节，文本 %2 字").arg(m_received).arg(m_text.size()));
        if (m_stream) {
            m_stream->end();
        }
        if (m_reply) {
            m_reply->deleteLater();
        }
    }

    void onClientGone()
    {
        if (m_done) {
            return;
        }
        m_done = true;
        Log::warn(QStringLiteral("客户端提前断开，中止上游"));
        if (m_reply) {
            m_reply->abort();
        }
    }

    /** 从 SSE 分块里提取 delta.content，拼成完整文本 */
    void accumulate(const QByteArray& chunk)
    {
        m_sse.append(chunk);
        int idx = -1;
        while ((idx = m_sse.indexOf('\n')) >= 0) {
            const QByteArray line = m_sse.left(idx).trimmed();
            m_sse.remove(0, idx + 1);
            if (!line.startsWith("data:")) {
                continue;
            }
            const QByteArray payload = line.mid(5).trimmed();
            if (payload.isEmpty() || payload == "[DONE]") {
                continue;
            }
            const QJsonDocument doc = QJsonDocument::fromJson(payload);
            const QJsonArray choices = doc.object().value(QStringLiteral("choices")).toArray();
            if (choices.isEmpty()) {
                continue;
            }
            const QJsonObject delta = choices.first().toObject().value(QStringLiteral("delta")).toObject();
            const QString content = delta.value(QStringLiteral("content")).toString();
            if (!content.isEmpty()) {
                m_text += content;
            }
        }
    }

    QTimer* m_keepAlive = nullptr;
    QPointer<QNetworkReply> m_reply;
    std::shared_ptr<HttpStream> m_stream;
    qint64 m_received = 0;
    bool m_done = false;
    QByteArray m_sse;
    QString m_text;
    std::function<void(const QString&)> m_onText;
};

} // namespace
AppController::AppController(QObject* parent)
    : QObject(parent)
{
}

AppController::~AppController() = default;

bool AppController::start()
{
    const QString exeDir = QCoreApplication::applicationDirPath();
    m_dataDir = exeDir + QStringLiteral("/data");
    QDir().mkpath(m_dataDir);

    Log::init(m_dataDir + QStringLiteral("/demon.log"));
    Log::info(QStringLiteral("Demon 启动，exe 目录：%1").arg(exeDir));

    // 单实例：避免用户重复双击导致“端口被占用”的困惑
    m_instanceLock = new QSharedMemory(QStringLiteral("DemonEngineInstance-v1"), this);
    if (!m_instanceLock->create(1)) {
        Log::warn(QStringLiteral("已有实例在运行，本次启动退出"));
        QMessageBox::information(
            nullptr, QStringLiteral("Demon"),
            QStringLiteral("Demon 已经在运行了。\n\n"
                           "如果没看到图标，请点任务栏右下角的 ^ 展开隐藏图标，\n"
                           "里面应该有一个紫色的 D。"));
        return false;
    }

    m_config = Config::load(exeDir + QStringLiteral("/config.json"));
    Log::info(QStringLiteral("配置：%1:%2  模型=%3  上游=%4 个")
                  .arg(m_config.host)
                  .arg(m_config.port)
                  .arg(m_config.modelId)
                  .arg(m_config.upstreams.size()));

    m_net = std::make_unique<QNetworkAccessManager>();

    setupVoice();

    m_server = std::make_unique<HttpServer>();
    m_server->setHandler([this](const HttpRequest& request) { return handleRequest(request); });
    m_server->setStreamHandler([this](const HttpRequest& request, const std::shared_ptr<HttpStream>& stream) {
        if (request.path == QStringLiteral("/voice/speak")) {
            return handleVoiceSpeak(request, stream);
        }
        return handleChatStream(request, stream);
    });

    if (!m_server->listen(m_config.host, m_config.port)) {
        const QString message = QStringLiteral("无法监听 %1:%2，端口可能被占用。\n\n"
                                               "最常见原因：已经有一个 Demon 在运行（看任务管理器）。\n"
                                               "或者别的程序占用了这个端口。\n\n"
                                               "解决办法：先退出已有的 Demon，或修改 config.json 里的 listen.port。")
                                    .arg(m_config.host)
                                    .arg(m_config.port);
        Log::error(message);
        QMessageBox::critical(nullptr, QStringLiteral("Demon 启动失败"), message);
        return false;
    }

    m_startedAtMs = QDateTime::currentMSecsSinceEpoch();
    Log::info(QStringLiteral("HTTP 服务已监听 http://%1:%2").arg(m_config.host).arg(m_server->port()));

    setupTray();

    m_window = std::make_unique<MainWindow>(this);
    m_window->show();

    auto* statusTimer = new QTimer(this);
    statusTimer->setInterval(2000);
    connect(statusTimer, &QTimer::timeout, this, [this]() { notifyUi(); });
    statusTimer->start();

    Log::info(QStringLiteral("主窗口已显示"));
    return true;
}

HttpResponse AppController::handleRequest(const HttpRequest& request)
{
    if (request.path == QStringLiteral("/healthz") || request.path == QStringLiteral("/health")) {
        return handleHealthz(request);
    }
    if (request.path == QStringLiteral("/v1/models") || request.path == QStringLiteral("/models")) {
        return handleModels(request);
    }
    if (request.path == QStringLiteral("/v1/chat/completions") || request.path == QStringLiteral("/chat/completions")) {
        return handleChatCompletions(request);
    }
    if (request.path == QStringLiteral("/launcher/open")) {
        const QString url = QStringLiteral("http://127.0.0.1:%1/").arg(m_config.launcher.stPort);
        openInEdge(url);
        HttpResponse response;
        response.body = QStringLiteral("{\"opened\":\"%1\"}").arg(url).toUtf8();
        return response;
    }
    if (request.path == QStringLiteral("/voice/status")) {
        return handleVoiceStatus(request);
    }
    if (request.path == QStringLiteral("/voice/speak")) {
        HttpResponse response;
        response.status = 405;
        response.body = jsonErrorBody(QStringLiteral("/voice/speak 只接受 POST"));
        return response;
    }
    if (request.path == QStringLiteral("/")) {
        HttpResponse response;
        response.contentType = QStringLiteral("text/plain; charset=utf-8");
        response.body = QStringLiteral("Demon engine is running.\n"
                                       "GET  /healthz\n"
                                       "GET  /v1/models\n"
                                       "POST /v1/chat/completions  (stream=true 走 SSE)\n")
                            .toUtf8();
        return response;
    }

    HttpResponse response;
    response.status = 404;
    response.body = jsonErrorBody(QStringLiteral("not found: %1").arg(request.path));
    return response;
}

HttpResponse AppController::handleHealthz(const HttpRequest&)
{
    const qint64 uptimeMs = QDateTime::currentMSecsSinceEpoch() - m_startedAtMs;
    const UpstreamConfig* up = pickUpstream(QString());

    const QString json = QStringLiteral(R"({
  "status": "ok",
  "version": "0.2.0",
  "uptimeSeconds": %1,
  "model": "%2",
  "upstreams": %3,
  "defaultUpstream": "%4",
  "upstreamBaseUrl": "%5",
  "voice": { "endpoint": "%6", "profile": "%7", "autoPlay": %8 }
})")
                             .arg(uptimeMs / 1000)
                             .arg(m_config.modelId)
                             .arg(m_config.upstreams.size())
                             .arg(m_config.effectiveUpstreamId())
                             .arg(up ? up->baseUrl : QString())
                             .arg(m_config.voice.endpoint, m_config.voice.profile)
                             .arg(m_config.voice.autoPlay ? QStringLiteral("true") : QStringLiteral("false"));

    HttpResponse response;
    response.body = json.toUtf8();
    return response;
}

HttpResponse AppController::handleModels(const HttpRequest&)
{
    const QString json = QStringLiteral(R"({
  "object": "list",
  "data": [
    { "id": "%1", "object": "model", "created": %2, "owned_by": "demon" }
  ]
})")
                             .arg(m_config.modelId)
                             .arg(m_startedAtMs / 1000);

    HttpResponse response;
    response.body = json.toUtf8();
    return response;
}

HttpResponse AppController::handleChatCompletions(const HttpRequest&)
{
    // 非流式请求暂不支持（酒馆默认走 stream=true）
    HttpResponse response;
    response.status = 501;
    response.body = jsonErrorBody(QStringLiteral("仅支持 stream=true（SSE）；非流式将在后续版本实现"));
    return response;
}

const UpstreamConfig* AppController::pickUpstream(const QString& modelFromRequest) const
{
    // 请求里的 model 若是某个上游的 id 或上游模型名，就路由到它；否则用默认
    if (!modelFromRequest.isEmpty()) {
        for (const UpstreamConfig& u : m_config.upstreams) {
            if (u.id == modelFromRequest || u.model == modelFromRequest) {
                return &u;
            }
        }
    }

    const QString id = m_config.effectiveUpstreamId();
    for (const UpstreamConfig& u : m_config.upstreams) {
        if (u.id == id) {
            return &u;
        }
    }
    return m_config.upstreams.isEmpty() ? nullptr : &m_config.upstreams.first();
}

QByteArray AppController::rewriteModel(const QByteArray& body, const QString& upstreamModel) const
{
    if (upstreamModel.isEmpty()) {
        return body;
    }
    QJsonParseError parseError{};
    const QJsonDocument doc = QJsonDocument::fromJson(body, &parseError);
    if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
        return body;
    }
    QJsonObject root = doc.object();
    root.insert(QStringLiteral("model"), upstreamModel);
    return QJsonDocument(root).toJson(QJsonDocument::Compact);
}

bool AppController::handleChatStream(const HttpRequest& request, const std::shared_ptr<HttpStream>& stream)
{
    if (request.path != QStringLiteral("/v1/chat/completions")
        && request.path != QStringLiteral("/chat/completions")) {
        return false;
    }

    QJsonParseError parseError{};
    const QJsonDocument doc = QJsonDocument::fromJson(request.body, &parseError);
    if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
        stream->writeHead(400, "application/json; charset=utf-8");
        stream->writeChunk(jsonErrorBody(QStringLiteral("请求体不是合法 JSON")));
        stream->end();
        return true;
    }

    const QJsonObject root = doc.object();

    // 记录本条回复应该用的声线（按角色绑定）
    m_pendingProfile = detectCharacterProfile(request.body);

    if (!root.value(QStringLiteral("stream")).toBool(false)) {
        return false; // 交给普通处理器（返回 501）
    }

    const UpstreamConfig* upstream = pickUpstream(root.value(QStringLiteral("model")).toString());
    if (!upstream) {
        stream->writeHead(503, "application/json; charset=utf-8");
        stream->writeChunk(jsonErrorBody(QStringLiteral("没有配置上游（config.json 的 upstreams 为空）")));
        stream->end();
        return true;
    }

    QUrl url(upstream->baseUrl);
    QString path = url.path();
    if (!path.endsWith(QLatin1Char('/'))) {
        path += QLatin1Char('/');
    }
    path += QStringLiteral("chat/completions");
    url.setPath(path);

    QNetworkRequest netRequest(url);
    netRequest.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    netRequest.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);
    if (!upstream->apiKey.isEmpty()) {
        netRequest.setRawHeader("Authorization", "Bearer " + upstream->apiKey.toUtf8());
    }

    const QByteArray payload = rewriteModel(request.body, upstream->model);
    Log::info(QStringLiteral("代理到上游 %1（model=%2）").arg(url.toString(), upstream->model));

    // 先把响应头发给客户端，再开始转发；否则 curl/酒馆会以为这不是 HTTP 响应
    stream->writeHead(200, "text/event-stream; charset=utf-8");

    QNetworkReply* reply = m_net->post(netRequest, payload);

    // 把转发工作交给一个独立的 job 对象（parent=reply，生命周期由 Qt 管理），
    // 避免闭包捕获局部变量导致的悬空指针。
    new StreamJob(reply, stream, this, [this](const QString& text) {
        Log::info(QStringLiteral("回调：收到完整文本 %1 字").arg(text.size()));
        onAssistantText(text);
    }, m_config.keepAliveSeconds * 1000);

    return true;
}


/* ------------------------------- 语音 ------------------------------- */

void AppController::setupVoice()
{
    m_tts = std::make_unique<TtsClient>();
    m_tts->setEndpoint(m_config.voice.endpoint);

    QVector<VoiceProfile> profiles;
    for (const VoiceProfileConfig& p : m_config.voiceProfiles) {
        VoiceProfile vp;
        vp.id = p.id;
        vp.name = p.name.isEmpty() ? p.id : p.name;
        vp.gptWeights = p.gptWeights;
        vp.sovitsWeights = p.sovitsWeights;
        vp.refAudio = p.refAudio;
        vp.promptText = p.promptText;
        vp.promptLang = p.promptLang;
        profiles.append(vp);
    }
    m_tts->setProfiles(profiles);

    m_activeProfile = m_config.voice.profile;
    if (m_tts->profile(m_activeProfile).id.isEmpty() && !profiles.isEmpty()) {
        m_activeProfile = profiles.first().id;
    }

    m_audio = std::make_unique<AudioPlayer>();
    m_audio->setVolume(m_config.voice.volume);

    Log::info(QStringLiteral("语音已配置：endpoint=%1 声线=%2 档案=%3 自动播放=%4")
                  .arg(m_config.voice.endpoint, m_activeProfile)
                  .arg(profiles.size())
                  .arg(m_config.voice.autoPlay ? QStringLiteral("是") : QStringLiteral("否")));
}

void AppController::onAssistantText(const QString& text)
{
    if (!m_config.voice.autoPlay || !m_tts) {
        return;
    }
    const QStringList sentences = splitForSpeech(text);
    if (sentences.isEmpty()) {
        return;
    }
    Log::info(QStringLiteral("准备朗读 %1 句（声线 %2）").arg(sentences.size()).arg(m_pendingProfile.isEmpty() ? m_activeProfile : m_pendingProfile));
    enqueueSpeech(sentences);
    pumpSpeech();
}

void AppController::enqueueSpeech(const QStringList& sentences)
{
    for (const QString& s : sentences) {
        const QString trimmed = s.trimmed();
        if (!trimmed.isEmpty()) {
            m_speechQueue.append(trimmed);
        }
    }
}

namespace {
/** 从 WAV 头估算播放时长（毫秒），失败返回 2000 */
int estimateWavMs(const QByteArray& wav)
{
    if (wav.size() < 44 || !wav.startsWith("RIFF")) {
        return 2000;
    }
    int pos = 12;
    int byteRate = 0;
    int dataSize = 0;
    while (pos + 8 <= wav.size()) {
        const QByteArray id = wav.mid(pos, 4);
        const int size = qFromLittleEndian<quint32>(reinterpret_cast<const uchar*>(wav.constData() + pos + 4));
        if (id == "fmt " && pos + 16 <= wav.size()) {
            byteRate = qFromLittleEndian<quint32>(reinterpret_cast<const uchar*>(wav.constData() + pos + 12));
        } else if (id == "data") {
            dataSize = size;
            break;
        }
        pos += 8 + size + (size & 1);
    }
    if (byteRate <= 0 || dataSize <= 0) {
        return 2000;
    }
    return qMax(400, static_cast<int>(static_cast<qint64>(dataSize) * 1000 / byteRate));
}
} // namespace

void AppController::pumpSpeech()
{
    if (m_synthBusy || m_speechQueue.isEmpty() || !m_tts) {
        return;
    }

    m_synthBusy = true;
    const QString sentence = m_speechQueue.takeFirst();
    const QString lang = detectTextLang(sentence);
    const QString profileId = m_pendingProfile.isEmpty() ? m_activeProfile : m_pendingProfile;
    const VoiceProfile profile = m_tts->profile(profileId);

    Log::info(QStringLiteral("合成[%1]：%2").arg(lang, sentence.left(24)));
    m_tts->ensureWeights(profile, [this, sentence, lang, profile](const QString& weightError) {
        if (!weightError.isEmpty()) {
            m_synthBusy = false;
            Log::warn(QStringLiteral("跳过该句：%1").arg(weightError));
            pumpSpeech();
            return;
        }
        m_tts->synthesize(sentence, lang, profile, m_config.voice.speed,
                          [this](const QByteArray& wav, const QString& error) {
                              m_synthBusy = false;
                              if (!error.isEmpty()) {
                                  Log::warn(QStringLiteral("跳过该句：%1").arg(error));
                                  pumpSpeech();
                                  return;
                              }
                              if (m_audio) {
                                  m_audio->playWav(wav);
                              }
                              const int ms = estimateWavMs(wav);
                              QTimer::singleShot(ms + 150, this, [this]() { pumpSpeech(); });
                          });
    });
}

HttpResponse AppController::handleVoiceStatus(const HttpRequest&)
{
    QJsonObject voice;
    voice.insert(QStringLiteral("endpoint"), m_config.voice.endpoint);
    voice.insert(QStringLiteral("profile"), m_activeProfile);
    voice.insert(QStringLiteral("autoPlay"), m_config.voice.autoPlay);
    voice.insert(QStringLiteral("speed"), m_config.voice.speed);
    voice.insert(QStringLiteral("queued"), m_speechQueue.size());
    voice.insert(QStringLiteral("busy"), m_synthBusy);

    QStringList ids;
    for (const VoiceProfileConfig& p : m_config.voiceProfiles) {
        ids.append(p.id);
    }
    voice.insert(QStringLiteral("profiles"), QJsonArray::fromStringList(ids));

    QJsonObject root;
    root.insert(QStringLiteral("voice"), voice);
    HttpResponse response;
    response.body = QJsonDocument(root).toJson(QJsonDocument::Compact);
    return response;
}

bool AppController::handleVoiceSpeak(const HttpRequest& request, const std::shared_ptr<HttpStream>& stream)
{
    if (request.method != QStringLiteral("POST")) {
        return false;
    }

    const QJsonObject body = QJsonDocument::fromJson(request.body).object();
    const QString text = body.value(QStringLiteral("text")).toString();
    if (text.trimmed().isEmpty()) {
        stream->writeHead(400, "application/json; charset=utf-8");
        stream->writeChunk(jsonErrorBody(QStringLiteral("text 不能为空")));
        stream->end();
        return true;
    }

    if (!m_tts) {
        stream->writeHead(503, "application/json; charset=utf-8");
        stream->writeChunk(jsonErrorBody(QStringLiteral("语音未初始化")));
        stream->end();
        return true;
    }

    QString profileId = body.value(QStringLiteral("profile")).toString();
    if (profileId.isEmpty()) {
        profileId = m_activeProfile;
    }
    const VoiceProfile profile = m_tts->profile(profileId);
    const QString lang = body.value(QStringLiteral("lang")).toString(detectTextLang(text));

    stream->writeHead(200, "audio/wav");
    m_tts->ensureWeights(profile, [this, text, lang, profile, stream](const QString& weightError) {
        if (!weightError.isEmpty()) {
            stream->writeHead(502, "application/json; charset=utf-8");
            stream->writeChunk(QStringLiteral("{\"error\":{\"message\":\"%1\"}}").arg(weightError).toUtf8());
            stream->end();
            return;
        }
    m_tts->synthesize(text, lang, profile, m_config.voice.speed,
                      [stream](const QByteArray& wav, const QString& error) {
                          if (!error.isEmpty()) {
                              stream->writeChunk(QStringLiteral("TTS 失败：%1").arg(error).toUtf8());
                          } else {
                              stream->writeChunk(wav);
                          }
                          stream->end();
                      });
    });
    return true;
}

/* ---------------------------- 控制窗口操作 ---------------------------- */

void AppController::applyProfile(const QString& id)
{
    m_activeProfile = id;
    m_config.voice.profile = id;
    m_config.save(m_config.filePath);
    Log::info(QStringLiteral("声线切换为 %1").arg(id));
    notifyUi();
}

void AppController::applyAutoPlay(bool on)
{
    m_config.voice.autoPlay = on;
    m_config.save(m_config.filePath);
    Log::info(QStringLiteral("自动朗读已%1").arg(on ? QStringLiteral("开启") : QStringLiteral("关闭")));
    notifyUi();
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
            vp.name = p.name.isEmpty() ? p.id : p.name;
            vp.gptWeights = p.gptWeights;
            vp.sovitsWeights = p.sovitsWeights;
            vp.refAudio = p.refAudio;
            vp.promptText = p.promptText;
            vp.promptLang = p.promptLang;
            profiles.append(vp);
        }
        m_tts->setProfiles(profiles);
    }
    m_activeProfile = m_config.voice.profile;
    Log::info(QStringLiteral("配置已重载"));
    notifyUi();
}


void AppController::setupTray()
{
    QPixmap pixmap(32, 32);
    pixmap.fill(Qt::transparent);
    {
        QPainter painter(&pixmap);
        painter.setRenderHint(QPainter::Antialiasing, true);
        QLinearGradient gradient(0, 0, 32, 32);
        gradient.setColorAt(0.0, QColor(0x6a, 0xa8, 0xff));
        gradient.setColorAt(1.0, QColor(0xa0, 0x6b, 0xff));
        painter.setBrush(gradient);
        painter.setPen(Qt::NoPen);
        painter.drawRoundedRect(QRect(0, 0, 32, 32), 8, 8);
        painter.setPen(Qt::white);
        QFont font = painter.font();
        font.setBold(true);
        font.setPixelSize(20);
        painter.setFont(font);
        painter.drawText(QRect(0, 0, 32, 32), Qt::AlignCenter, QStringLiteral("D"));
    }

    m_menu = new QMenu();
    m_statusAction = m_menu->addAction(
        QStringLiteral("监听 http://%1:%2").arg(m_config.host).arg(m_config.port));
    m_statusAction->setEnabled(false);

    m_voiceMenu = m_menu->addMenu(QStringLiteral("声线"));
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

    QAction* showPanel = m_menu->addAction(QStringLiteral("显示控制面板"));
    connect(showPanel, &QAction::triggered, this, [this]() {
        if (m_window) {
            m_window->show();
            m_window->raise();
            m_window->activateWindow();
        }
    });

    QAction* openLog = m_menu->addAction(QStringLiteral("打开日志"));
    connect(openLog, &QAction::triggered, this, []() {
        QProcess::startDetached(QStringLiteral("notepad.exe"),
                                {QCoreApplication::applicationDirPath() + QStringLiteral("/data/demon.log")});
    });

    QAction* openConfig = m_menu->addAction(QStringLiteral("打开配置目录"));
    connect(openConfig, &QAction::triggered, this, []() {
        QProcess::startDetached(QStringLiteral("explorer.exe"), {QCoreApplication::applicationDirPath()});
    });

    QAction* reload = m_menu->addAction(QStringLiteral("重载配置"));
    connect(reload, &QAction::triggered, this, [this]() {
        m_config = Config::load(QCoreApplication::applicationDirPath() + QStringLiteral("/config.json"));
        Log::info(QStringLiteral("配置已重载"));
        showStatus();
    });

    m_menu->addSeparator();

    QAction* quit = m_menu->addAction(QStringLiteral("退出"));
    connect(quit, &QAction::triggered, qApp, &QApplication::quit);

    m_tray = new QSystemTrayIcon(QIcon(pixmap), this);
    m_tray->setToolTip(QStringLiteral("Demon"));
    m_tray->setContextMenu(m_menu);
    connect(m_tray, &QSystemTrayIcon::activated, this, [this](QSystemTrayIcon::ActivationReason reason) {
        if (reason == QSystemTrayIcon::Trigger) {
            showStatus();
        } else if (reason == QSystemTrayIcon::DoubleClick && m_window) {
            m_window->show();
            m_window->raise();
            m_window->activateWindow();
        }
    });
    m_tray->show();
    m_tray->showMessage(
        QStringLiteral("Demon 已启动"),
        QStringLiteral("右键托盘里的 D 图标：切换声线 / 开关朗读 / 看日志。\n"
                       "如果没看到图标，点任务栏右下角的 ^ 展开隐藏图标。"),
        QSystemTrayIcon::Information, 8000);

    Log::info(QStringLiteral("托盘诊断：isVisible=%1 iconNull=%2 geometryValid=%3")
                  .arg(m_tray->isVisible() ? 1 : 0)
                  .arg(m_tray->icon().isNull() ? 1 : 0)
                  .arg(m_tray->geometry().isValid() ? 1 : 0));
    Log::info(QStringLiteral("托盘已创建（系统托盘可用=%1，支持气泡=%2）")
                  .arg(QSystemTrayIcon::isSystemTrayAvailable() ? QStringLiteral("是") : QStringLiteral("否"),
                       QSystemTrayIcon::supportsMessages() ? QStringLiteral("是") : QStringLiteral("否")));
}

void AppController::showStatus()
{
    if (!m_tray) {
        return;
    }
    const UpstreamConfig* up = pickUpstream(QString());
    m_tray->showMessage(QStringLiteral("Demon"),
                        QStringLiteral("引擎运行中\n%1:%2\n模型：%3\n上游：%4")
                            .arg(m_config.host)
                            .arg(m_config.port)
                            .arg(m_config.modelId)
                            .arg(up ? up->baseUrl : QStringLiteral("未配置")),
                        QSystemTrayIcon::Information, 4000);
}


bool AppController::portOpen(quint16 port)
{
    QTcpSocket socket;
    socket.connectToHost(QStringLiteral("127.0.0.1"), port);
    const bool ok = socket.waitForConnected(300);
    socket.abort();
    return ok;
}

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

namespace {

/** 从注册表读默认浏览器的可执行路径（取命令行的第一个 exe） */
QString defaultBrowserExe()
{
    QString progId;
    {
        QSettings assoc(QStringLiteral("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\http\\UserChoice"),
                        QSettings::NativeFormat);
        progId = assoc.value(QStringLiteral("ProgId")).toString();
    }
    if (progId.isEmpty()) {
        return QString();
    }
    QSettings cmd(QStringLiteral("HKEY_CLASSES_ROOT\\%1\\shell\\open\\command").arg(progId),
                  QSettings::NativeFormat);
    const QString command = cmd.value(QStringLiteral(".")).toString();
    if (command.isEmpty()) {
        return QString();
    }
    // 形如 "C:\...\msedge.exe" --single-argument %1
    QString exe;
    if (command.startsWith(QLatin1Char('"'))) {
        const int closing = command.indexOf(QLatin1Char('"'), 1);
        if (closing > 0) {
            exe = command.mid(1, closing - 1);
        }
    } else {
        exe = command.section(QLatin1Char(' '), 0, 0);
    }
    return QFile::exists(exe) ? exe : QString();
}

} // namespace

namespace {

/** 用 Win32 CreateProcess 启动一条命令行（不依赖 Qt 的 detached 逻辑） */
bool spawnCommandLine(const QString& commandLine)
{
#ifdef Q_OS_WIN
    std::wstring cmd = commandLine.toStdWString();
    STARTUPINFOW si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    const BOOL ok = CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, FALSE,
                                   CREATE_NEW_PROCESS_GROUP | CREATE_UNICODE_ENVIRONMENT,
                                   nullptr, nullptr, &si, &pi);
    if (!ok) {
        Log::warn(QStringLiteral("CreateProcessW 失败，错误码 %1").arg(GetLastError()));
        return false;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return true;
#else
    Q_UNUSED(commandLine);
    return false;
#endif
}

} // namespace

int AppController::browserProcessCount()
{
    QProcess list;
    list.start(QStringLiteral("tasklist"));
    if (!list.waitForFinished(4000)) {
        return -1;
    }
    const QString out = QString::fromLocal8Bit(list.readAllStandardOutput()).toLower();
    const QStringList names{
        QStringLiteral("msedge.exe"), QStringLiteral("chrome.exe"), QStringLiteral("firefox.exe"),
        QStringLiteral("brave.exe"), QStringLiteral("vivaldi.exe"), QStringLiteral("opera.exe"),
        QStringLiteral("360se.exe"), QStringLiteral("360chrome.exe"), QStringLiteral("qqbrowser.exe")
    };
    int count = 0;
    for (const QString& name : names) {
        count += out.count(name);
    }
    return count;
}

bool AppController::openInEdge(const QString& url)
{
    const QStringList candidates{
        QStringLiteral("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        QStringLiteral("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    };
    for (const QString& exe : candidates) {
        if (!QFile::exists(exe)) {
            continue;
        }
        // --app 模式：独立窗口、无地址栏、无标签页，看起来像内置浏览器
        const QString line = QStringLiteral("cmd.exe /c start \"\" \"%1\" --app=%2").arg(exe, url);
        if (spawnCommandLine(line)) {
            Log::info(QStringLiteral("已用 Edge --app 打开：%1").arg(url));
            return true;
        }
    }
    Log::warn(QStringLiteral("没找到 Edge，回退默认浏览器"));
    return openExternalUrl(url);
}

bool AppController::openExternalUrl(const QString& url)
{
    // 直接落到浏览器 exe（路径带空格，必须加引号）；壳层激活在这台机器上不可靠。
    const QString browser = defaultBrowserExe();
    if (!browser.isEmpty()) {
        const QString line = QStringLiteral("cmd.exe /c start \"\" \"%1\" \"%2\"").arg(browser, url);
        if (spawnCommandLine(line)) {
            Log::info(QStringLiteral("已启动浏览器 %1 打开 %2").arg(browser, url));
            return true;
        }
    }

    const QString line = QStringLiteral("cmd.exe /c start \"\" \"%1\"").arg(url);
    if (spawnCommandLine(line)) {
        Log::info(QStringLiteral("已通过 cmd start 打开：%1").arg(url));
        return true;
    }

    const bool ok = QDesktopServices::openUrl(QUrl(url));
    Log::info(QStringLiteral("QDesktopServices 结果：%1").arg(ok ? QStringLiteral("成功") : QStringLiteral("失败")));
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
