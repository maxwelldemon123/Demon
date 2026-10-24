#include "Config.h"

#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

QString Config::effectiveUpstreamId() const
{
    if (!defaultUpstreamId.isEmpty()) {
        return defaultUpstreamId;
    }
    return upstreams.isEmpty() ? QString() : upstreams.first().id;
}

Config Config::load(const QString& filePath)
{
    Config cfg;
    cfg.filePath = filePath;

    QFile file(filePath);
    if (!file.exists() || !file.open(QIODevice::ReadOnly)) {
        // 首次运行：给一个本地上游示例，便于命令行验证
        UpstreamConfig local;
        local.id = QStringLiteral("local");
        local.baseUrl = QStringLiteral("http://127.0.0.1:8080/v1");
        local.model = QStringLiteral("local-model");
        cfg.upstreams.append(local);
        cfg.defaultUpstreamId = local.id;

        VoiceProfileConfig xiaod;
        xiaod.id = QStringLiteral("xiaod");
        xiaod.refAudio = QStringLiteral("refs/xiaod.wav");
        xiaod.promptText = QStringLiteral("私を強くして……どうするつもりですか？");
        xiaod.promptLang = QStringLiteral("ja");
        cfg.voiceProfiles.append(xiaod);

        VoiceProfileConfig demon;
        demon.id = QStringLiteral("demon");
        demon.refAudio = QStringLiteral("refs/demon.wav");
        demon.promptText = QStringLiteral("この人たちが敵ね。へーえ、面白そうじゃない。");
        demon.promptLang = QStringLiteral("ja");
        cfg.voiceProfiles.append(demon);
        cfg.save(filePath);
        return cfg;
    }

    const QJsonDocument doc = QJsonDocument::fromJson(file.readAll());
    const QJsonObject root = doc.object();

    const QJsonObject listen = root.value(QStringLiteral("listen")).toObject();
    if (!listen.isEmpty()) {
        cfg.host = listen.value(QStringLiteral("host")).toString(cfg.host);
        cfg.port = static_cast<quint16>(listen.value(QStringLiteral("port")).toInt(cfg.port));
    }

    cfg.modelId = root.value(QStringLiteral("modelId")).toString(cfg.modelId);
    cfg.defaultUpstreamId = root.value(QStringLiteral("defaultUpstream")).toString();

    const QJsonArray ups = root.value(QStringLiteral("upstreams")).toArray();
    for (const QJsonValue& v : ups) {
        const QJsonObject o = v.toObject();
        UpstreamConfig u;
        u.id = o.value(QStringLiteral("id")).toString();
        u.baseUrl = o.value(QStringLiteral("baseUrl")).toString();
        u.model = o.value(QStringLiteral("model")).toString();
        u.apiKey = o.value(QStringLiteral("apiKey")).toString();
        if (!u.id.isEmpty() && !u.baseUrl.isEmpty()) {
            cfg.upstreams.append(u);
        }
    }

    const QJsonObject voice = root.value(QStringLiteral("voice")).toObject();
    if (!voice.isEmpty()) {
        cfg.voice.endpoint = voice.value(QStringLiteral("endpoint")).toString(cfg.voice.endpoint);
        cfg.voice.profile = voice.value(QStringLiteral("profile")).toString(cfg.voice.profile);
        cfg.voice.autoPlay = voice.value(QStringLiteral("autoPlay")).toBool(cfg.voice.autoPlay);
        cfg.voice.speed = voice.value(QStringLiteral("speed")).toDouble(cfg.voice.speed);
        cfg.voice.volume = voice.value(QStringLiteral("volume")).toDouble(cfg.voice.volume);
    }

    const QJsonArray profiles = root.value(QStringLiteral("voiceProfiles")).toArray();
    for (const QJsonValue& v : profiles) {
        const QJsonObject o = v.toObject();
        VoiceProfileConfig p;
        p.id = o.value(QStringLiteral("id")).toString();
        p.name = o.value(QStringLiteral("name")).toString();
        p.gptWeights = o.value(QStringLiteral("gptWeights")).toString();
        p.sovitsWeights = o.value(QStringLiteral("sovitsWeights")).toString();
        p.refAudio = o.value(QStringLiteral("refAudio")).toString();
        p.promptText = o.value(QStringLiteral("promptText")).toString();
        p.promptLang = o.value(QStringLiteral("promptLang")).toString(QStringLiteral("ja"));
        if (!p.id.isEmpty() && !p.refAudio.isEmpty()) {
            cfg.voiceProfiles.append(p);
        }
    }

    if (cfg.voiceProfiles.isEmpty()) {
        VoiceProfileConfig xiaod;
        xiaod.id = QStringLiteral("xiaod");
        xiaod.refAudio = QStringLiteral("refs/xiaod.wav");
        xiaod.promptText = QStringLiteral("私を強くして……どうするつもりですか？");
        cfg.voiceProfiles.append(xiaod);

        VoiceProfileConfig demon;
        demon.id = QStringLiteral("demon");
        demon.refAudio = QStringLiteral("refs/demon.wav");
        demon.promptText = QStringLiteral("この人たちが敵ね。へーえ、面白そうじゃない。");
        cfg.voiceProfiles.append(demon);
    }

    const QJsonObject launcher = root.value(QStringLiteral("launcher")).toObject();
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

    const QJsonObject engine = root.value(QStringLiteral("engine")).toObject();
    if (!engine.isEmpty()) {
        cfg.keepAliveSeconds = engine.value(QStringLiteral("keepAliveSeconds")).toInt(cfg.keepAliveSeconds);
        cfg.requestTimeoutSeconds = engine.value(QStringLiteral("requestTimeoutSeconds")).toInt(cfg.requestTimeoutSeconds);
    }

    return cfg;
}

QString Config::toJson() const
{
    QJsonObject root;
    QJsonObject listen;
    listen.insert(QStringLiteral("host"), host);
    listen.insert(QStringLiteral("port"), port);
    root.insert(QStringLiteral("listen"), listen);
    root.insert(QStringLiteral("modelId"), modelId);

    QJsonArray ups;
    for (const UpstreamConfig& u : upstreams) {
        QJsonObject o;
        o.insert(QStringLiteral("id"), u.id);
        o.insert(QStringLiteral("baseUrl"), u.baseUrl);
        o.insert(QStringLiteral("model"), u.model);
        o.insert(QStringLiteral("apiKey"), u.apiKey);
        ups.append(o);
    }
    root.insert(QStringLiteral("upstreams"), ups);
    root.insert(QStringLiteral("defaultUpstream"), effectiveUpstreamId());

    QJsonObject voice;
    voice.insert(QStringLiteral("endpoint"), this->voice.endpoint);
    voice.insert(QStringLiteral("profile"), this->voice.profile);
    voice.insert(QStringLiteral("autoPlay"), this->voice.autoPlay);
    voice.insert(QStringLiteral("speed"), this->voice.speed);
    voice.insert(QStringLiteral("volume"), this->voice.volume);
    root.insert(QStringLiteral("voice"), voice);

    QJsonArray profilesOut;
    for (const VoiceProfileConfig& p : voiceProfiles) {
        QJsonObject o;
        o.insert(QStringLiteral("id"), p.id);
        o.insert(QStringLiteral("name"), p.name);
        o.insert(QStringLiteral("gptWeights"), p.gptWeights);
        o.insert(QStringLiteral("sovitsWeights"), p.sovitsWeights);
        o.insert(QStringLiteral("refAudio"), p.refAudio);
        o.insert(QStringLiteral("promptText"), p.promptText);
        o.insert(QStringLiteral("promptLang"), p.promptLang);
        profilesOut.append(o);
    }
    root.insert(QStringLiteral("voiceProfiles"), profilesOut);

    QJsonObject launcherOut;
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
    engine.insert(QStringLiteral("keepAliveSeconds"), keepAliveSeconds);
    engine.insert(QStringLiteral("requestTimeoutSeconds"), requestTimeoutSeconds);
    root.insert(QStringLiteral("engine"), engine);

    return QString::fromUtf8(QJsonDocument(root).toJson(QJsonDocument::Indented));
}

bool Config::save(const QString& filePath) const
{
    QFile file(filePath);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        return false;
    }
    file.write(toJson().toUtf8());
    return true;
}
