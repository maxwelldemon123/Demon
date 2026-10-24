#pragma once

#include <QMap>
#include <QString>
#include <QVector>

/**
 * 运行配置：<exe 目录>/config.json
 * 缺省时使用内置默认值，并在首次启动时写一份示例。
 */
struct UpstreamConfig {
    QString id;
    QString baseUrl;   // 例如 http://127.0.0.1:8080/v1
    QString model;     // 上游模型名
    QString apiKey;
};

struct VoiceProfileConfig {
    QString id;
    QString name;         // 显示名（可空，空则用 id）
    QString gptWeights;   // GPT 权重（相对 api_v2 的 cwd 或绝对路径），可空
    QString sovitsWeights;// SoVITS 权重，可空
    QString refAudio;     // 参考音频（相对 api_v2 的 cwd 或绝对路径）
    QString promptText;   // 参考音频原文
    QString promptLang = QStringLiteral("ja");
};

struct LauncherConfig {
    QString stPath = QStringLiteral("C:\\mylove\\SillyTavern");
    int stPort = 8000;
    QString gsvPath = QStringLiteral("E:\\GPT-SoVITS-v5-20261005\\GPT-SoVITS-v2pro-20261006");
};

struct VoiceConfig {
    QString endpoint = QStringLiteral("http://127.0.0.1:9880");
    QString profile = QStringLiteral("xiaod");
    bool autoPlay = true;
    double speed = 1.0;
    double volume = 1.0;
};

class Config {
public:
    static Config load(const QString& filePath);

    bool save(const QString& filePath) const;
    QString toJson() const;

    QString filePath;

    // 监听
    QString host = QStringLiteral("127.0.0.1");
    quint16 port = 8790;

    // 对外声明的模型名（酒馆下拉框里显示）
    QString modelId = QStringLiteral("demon");

    // 上游
    QVector<UpstreamConfig> upstreams;
    QString defaultUpstreamId;

    // 语音
    VoiceConfig voice;
    QVector<VoiceProfileConfig> voiceProfiles;

    // 启动器
    LauncherConfig launcher;

    // 角色声线绑定：角色名 -> 档案 id
    QMap<QString, QString> characterVoices;

    // 角色卡目录（空则用 <stPath>\data\default-user\characters）
    QString charactersDir;

    // 其它
    int keepAliveSeconds = 15;
    int requestTimeoutSeconds = 180;

    /** 找默认上游；没有则返回空 id */
    QString effectiveUpstreamId() const;
};
