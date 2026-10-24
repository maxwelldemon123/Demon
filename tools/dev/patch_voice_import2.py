# -*- coding: utf-8 -*-
"""TtsClient::ensureWeights 实现 + AppController 组装档案时带权重。"""

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


impl = r'''
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
'''

P = f"{ROOT}\\src\\voice\\TtsClient.cpp"
t = io.open(P, encoding="utf-8").read()
if "TtsClient::ensureWeights" not in t:
    t = t.replace("void TtsClient::probe(", impl + "\nvoid TtsClient::probe(", 1)
    if "#include <QUrlQuery>" not in t:
        t = t.replace("#include <QUrl>", "#include <QUrl>\n#include <QUrlQuery>")
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("[OK] TtsClient.cpp")

# AppController：组装档案时带 name / weights
P2 = f"{ROOT}\\src\\app\\AppController.cpp"
t2 = io.open(P2, encoding="utf-8").read()
old = """        VoiceProfile vp;
        vp.id = p.id;
        vp.refAudio = p.refAudio;
        vp.promptText = p.promptText;
        vp.promptLang = p.promptLang;
        profiles.append(vp);"""
new = """        VoiceProfile vp;
        vp.id = p.id;
        vp.name = p.name.isEmpty() ? p.id : p.name;
        vp.gptWeights = p.gptWeights;
        vp.sovitsWeights = p.sovitsWeights;
        vp.refAudio = p.refAudio;
        vp.promptText = p.promptText;
        vp.promptLang = p.promptLang;
        profiles.append(vp);"""
if old in t2:
    t2 = t2.replace(old, new)
    print("[OK] AppController setupVoice 档案")
else:
    print("[warn] setupVoice 锚点未命中")

old2 = """            VoiceProfile vp;
            vp.id = p.id;
            vp.refAudio = p.refAudio;
            vp.promptText = p.promptText;
            vp.promptLang = p.promptLang;
            profiles.append(vp);"""
new2 = """            VoiceProfile vp;
            vp.id = p.id;
            vp.name = p.name.isEmpty() ? p.id : p.name;
            vp.gptWeights = p.gptWeights;
            vp.sovitsWeights = p.sovitsWeights;
            vp.refAudio = p.refAudio;
            vp.promptText = p.promptText;
            vp.promptLang = p.promptLang;
            profiles.append(vp);"""
if old2 in t2:
    t2 = t2.replace(old2, new2)
    print("[OK] reloadConfig 档案")

# 合成前先切权重
old3 = """    Log::info(QStringLiteral("合成[%1]：%2").arg(lang, sentence.left(24)));
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
                      });"""
new3 = """    Log::info(QStringLiteral("合成[%1]：%2").arg(lang, sentence.left(24)));
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
    });"""
if old3 in t2:
    t2 = t2.replace(old3, new3)
    print("[OK] pumpSpeech 先切权重")
else:
    print("[warn] pumpSpeech 锚点未命中")

# /voice/speak 也要先切权重
old4 = """    m_tts->synthesize(text, lang, profile, m_config.voice.speed,
                      [stream](const QByteArray& wav, const QString& error) {"""
new4 = """    m_tts->ensureWeights(profile, [this, text, lang, profile, stream](const QString& weightError) {
        if (!weightError.isEmpty()) {
            stream->writeHead(502, "application/json; charset=utf-8");
            stream->writeChunk(QStringLiteral("{\\"error\\":{\\"message\\":\\"%1\\"}}").arg(weightError).toUtf8());
            stream->end();
            return;
        }
    m_tts->synthesize(text, lang, profile, m_config.voice.speed,
                      [stream](const QByteArray& wav, const QString& error) {"""
if old4 in t2:
    t2 = t2.replace(old4, new4)
    # 补上闭合括号
    old5 = """                          stream->end();
                      });
    return true;
}"""
    new5 = """                          stream->end();
                      });
    });
    return true;
}"""
    if old5 in t2:
        t2 = t2.replace(old5, new5, 1)
        print("[OK] /voice/speak 先切权重")
    else:
        print("[warn] speak 闭合锚点未命中")

io.open(P2, "w", encoding="utf-8", newline="").write(t2)
print("patch phase 2 done")
