#pragma once

#include <QByteArray>
#include <QJsonObject>
#include <QObject>
#include <QString>
#include <QVector>

#include <functional>

class QNetworkAccessManager;
class QNetworkReply;

/** 一条声线档案 */
struct VoiceProfile {
    QString id;          // 档案 id
    QString name;        // 显示名
    QString gptWeights;  // 可空：切换 GPT 权重
    QString sovitsWeights;
    QString refAudio;    // 绝对路径，交给 api_v2
    QString promptText;  // 参考音频原文
    QString promptLang = QStringLiteral("ja");
};

/** 一句待合成的文本 */
struct SpeechChunk {
    QString text;
    QString lang; // zh / ja / en ...
};

/**
 * GPT-SoVITS api_v2 客户端：
 *   POST {endpoint}/tts  →  WAV 字节
 * 只负责“合成”，播放交给 AudioPlayer。
 */
class TtsClient : public QObject {
    Q_OBJECT

public:
    explicit TtsClient(QObject* parent = nullptr);

    void setEndpoint(const QString& endpoint) { m_endpoint = endpoint; }
    QString endpoint() const { return m_endpoint; }

    void setProfiles(const QVector<VoiceProfile>& profiles) { m_profiles = profiles; }
    QVector<VoiceProfile> profiles() const { return m_profiles; }

    VoiceProfile profile(const QString& id) const;
    QString defaultProfileId() const;

    /** 合成一句；回调返回 WAV（失败时 error 非空） */
    void synthesize(const QString& text, const QString& lang, const VoiceProfile& profile,
                    double speed, std::function<void(const QByteArray& wav, const QString& error)> callback);

    /** 探测服务是否在线（GET /control） */
    void probe(std::function<void(bool ok)> callback);

    /** 确保当前加载的是该档案的权重；不一样时先切换再回调 */
    void ensureWeights(const VoiceProfile& profile, std::function<void(const QString& error)> callback);

private:
    QNetworkAccessManager* m_net = nullptr;
    QString m_endpoint = QStringLiteral("http://127.0.0.1:9880");
    QVector<VoiceProfile> m_profiles;
    QString m_loadedGpt;
    QString m_loadedSovits;
};
