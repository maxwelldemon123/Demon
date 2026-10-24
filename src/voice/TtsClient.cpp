#include "TtsClient.h"

#include "../util/Log.h"

#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>
#include <QUrlQuery>

TtsClient::TtsClient(QObject* parent)
    : QObject(parent)
    , m_net(new QNetworkAccessManager(this))
{
}

VoiceProfile TtsClient::profile(const QString& id) const
{
    for (const VoiceProfile& p : m_profiles) {
        if (p.id == id) {
            return p;
        }
    }
    return m_profiles.isEmpty() ? VoiceProfile{} : m_profiles.first();
}

QString TtsClient::defaultProfileId() const
{
    return m_profiles.isEmpty() ? QStringLiteral("xiaod") : m_profiles.first().id;
}

void TtsClient::synthesize(const QString& text, const QString& lang, const VoiceProfile& profile,
                           double speed, std::function<void(const QByteArray&, const QString&)> callback)
{
    QJsonObject body;
    body.insert(QStringLiteral("text"), text);
    body.insert(QStringLiteral("text_lang"), lang);
    body.insert(QStringLiteral("ref_audio_path"), profile.refAudio);
    body.insert(QStringLiteral("prompt_text"), profile.promptText);
    body.insert(QStringLiteral("prompt_lang"), profile.promptLang);
    body.insert(QStringLiteral("text_split_method"), QStringLiteral("cut5"));
    body.insert(QStringLiteral("batch_size"), 1);
    body.insert(QStringLiteral("media_type"), QStringLiteral("wav"));
    body.insert(QStringLiteral("streaming_mode"), 0);
    body.insert(QStringLiteral("speed_factor"), speed);
    body.insert(QStringLiteral("top_k"), 15);
    body.insert(QStringLiteral("top_p"), 1);
    body.insert(QStringLiteral("temperature"), 1);
    body.insert(QStringLiteral("repetition_penalty"), 1.35);
    body.insert(QStringLiteral("seed"), -1);
    body.insert(QStringLiteral("parallel_infer"), true);

    QUrl url(m_endpoint);
    QString path = url.path();
    if (path.endsWith(QLatin1Char('/'))) {
        path.chop(1);
    }
    path += QStringLiteral("/tts");
    url.setPath(path);

    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    QNetworkReply* reply = m_net->post(request, QJsonDocument(body).toJson(QJsonDocument::Compact));

    auto buffer = std::make_shared<QByteArray>();
    connect(reply, &QNetworkReply::readyRead, reply, [reply, buffer]() { buffer->append(reply->readAll()); });
    connect(reply, &QNetworkReply::finished, reply, [this, reply, buffer, text, callback]() {
        if (reply->error() == QNetworkReply::NoError) {
            buffer->append(reply->readAll());
            if (buffer->isEmpty()) {
                callback(QByteArray(), QStringLiteral("合成返回空音频"));
            } else {
                Log::info(QStringLiteral("TTS 合成完成：%1 字 / %2 KB").arg(text.size()).arg(buffer->size() / 1024));
                callback(*buffer, QString());
            }
        } else {
            const QString error = QStringLiteral("%1（%2）").arg(reply->errorString()).arg(m_endpoint);
            Log::error(QStringLiteral("TTS 失败：%1").arg(error));
            callback(QByteArray(), error);
        }
        reply->deleteLater();
    });
}


void TtsClient::ensureWeights(const VoiceProfile& profile, std::function<void(const QString&)> callback)
{
    const QString wantGpt = profile.gptWeights.trimmed();
    const QString wantSovits = profile.sovitsWeights.trimmed();

    // 依次设置 GPT、SoVITS；都不需要切换时直接回调
    std::function<void(const QString&)> setSovits = [this, wantSovits, callback](const QString&) {
        if (wantSovits.isEmpty() || wantSovits == m_loadedSovits) {
            callback(QString());
            return;
        }
        QUrl url(m_endpoint);
        QString path = url.path();
        if (path.endsWith(QLatin1Char('/'))) {
            path.chop(1);
        }
        url.setPath(path + QStringLiteral("/set_sovits_weights"));
        QUrlQuery query;
        query.addQueryItem(QStringLiteral("weights_path"), wantSovits);
        url.setQuery(query);

        QNetworkReply* reply = m_net->get(QNetworkRequest(url));
        connect(reply, &QNetworkReply::finished, reply, [this, reply, wantSovits, callback]() {
            const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
            if (reply->error() != QNetworkReply::NoError && status != 400) {
                const QString err = QStringLiteral("设置 SoVITS 权重失败：%1").arg(reply->errorString());
                Log::error(err);
                callback(err);
            } else {
                m_loadedSovits = wantSovits;
                Log::info(QStringLiteral("权重已切换：%1").arg(wantSovits));
                callback(QString());
            }
            reply->deleteLater();
        });
    };

    if (wantGpt.isEmpty() || wantGpt == m_loadedGpt) {
        setSovits(QString());
        return;
    }

    QUrl url(m_endpoint);
    QString path = url.path();
    if (path.endsWith(QLatin1Char('/'))) {
        path.chop(1);
    }
    url.setPath(path + QStringLiteral("/set_gpt_weights"));
    QUrlQuery query;
    query.addQueryItem(QStringLiteral("weights_path"), wantGpt);
    url.setQuery(query);

    QNetworkReply* reply = m_net->get(QNetworkRequest(url));
    connect(reply, &QNetworkReply::finished, reply, [this, reply, wantGpt, setSovits]() {
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        if (reply->error() != QNetworkReply::NoError && status != 400) {
            const QString err = QStringLiteral("设置 GPT 权重失败：%1").arg(reply->errorString());
            Log::error(err);
            setSovits(err);
        } else {
            m_loadedGpt = wantGpt;
            Log::info(QStringLiteral("权重已切换：%1").arg(wantGpt));
            setSovits(QString());
        }
        reply->deleteLater();
    });
}

void TtsClient::probe(std::function<void(bool)> callback)
{
    QUrl url(m_endpoint);
    QString path = url.path();
    if (path.endsWith(QLatin1Char('/'))) {
        path.chop(1);
    }
    path += QStringLiteral("/control");
    url.setPath(path);

    QNetworkRequest request(url);
    QNetworkReply* reply = m_net->get(request);
    connect(reply, &QNetworkReply::finished, reply, [reply, callback]() {
        // 400 也算“活着”
        const bool ok = reply->error() == QNetworkReply::NoError
            || reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() > 0;
        callback(ok);
        reply->deleteLater();
    });
}
