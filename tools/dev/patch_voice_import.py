# -*- coding: utf-8 -*-
"""把插件里的音色档案搬进 Demon：
1) Config 增加 gptWeights / sovitsWeights
2) TtsClient 支持切换权重（set_gpt_weights / set_sovits_weights）
3) AppController 组装档案时带上权重
"""

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


# ---------------- Config ----------------
patch("src\\config\\Config.h", [(
"""struct VoiceProfileConfig {
    QString id;
    QString refAudio;     // 参考音频（相对 api_v2 的 cwd 或绝对路径）
    QString promptText;   // 参考音频原文
    QString promptLang = QStringLiteral("ja");
};""",
"""struct VoiceProfileConfig {
    QString id;
    QString name;         // 显示名（可空，空则用 id）
    QString gptWeights;   // GPT 权重（相对 api_v2 的 cwd 或绝对路径），可空
    QString sovitsWeights;// SoVITS 权重，可空
    QString refAudio;     // 参考音频（相对 api_v2 的 cwd 或绝对路径）
    QString promptText;   // 参考音频原文
    QString promptLang = QStringLiteral("ja");
};""",
"档案字段")])

patch("src\\config\\Config.cpp", [
(
"""        p.id = o.value(QStringLiteral("id")).toString();
        p.refAudio = o.value(QStringLiteral("refAudio")).toString();""",
"""        p.id = o.value(QStringLiteral("id")).toString();
        p.name = o.value(QStringLiteral("name")).toString();
        p.gptWeights = o.value(QStringLiteral("gptWeights")).toString();
        p.sovitsWeights = o.value(QStringLiteral("sovitsWeights")).toString();
        p.refAudio = o.value(QStringLiteral("refAudio")).toString();""",
"解析权重"),
(
"""        o.insert(QStringLiteral("id"), p.id);
        o.insert(QStringLiteral("refAudio"), p.refAudio);""",
"""        o.insert(QStringLiteral("id"), p.id);
        o.insert(QStringLiteral("name"), p.name);
        o.insert(QStringLiteral("gptWeights"), p.gptWeights);
        o.insert(QStringLiteral("sovitsWeights"), p.sovitsWeights);
        o.insert(QStringLiteral("refAudio"), p.refAudio);""",
"序列化权重"),
])

# ---------------- TtsClient.h ----------------
patch("src\\voice\\TtsClient.h", [
(
"""struct VoiceProfile {
    QString id;          // xiaod / demon
    QString refAudio;    // 绝对路径，交给 api_v2
    QString promptText;  // 参考音频原文
    QString promptLang = QStringLiteral("ja");
};""",
"""struct VoiceProfile {
    QString id;          // 档案 id
    QString name;        // 显示名
    QString gptWeights;  // 可空：切换 GPT 权重
    QString sovitsWeights;
    QString refAudio;    // 绝对路径，交给 api_v2
    QString promptText;  // 参考音频原文
    QString promptLang = QStringLiteral("ja");
};""",
"档案字段加权重"),
(
"""    /** 探测服务是否在线（GET /control） */
    void probe(std::function<void(bool ok)> callback);""",
"""    /** 探测服务是否在线（GET /control） */
    void probe(std::function<void(bool ok)> callback);

    /** 确保当前加载的是该档案的权重；不一样时先切换再回调 */
    void ensureWeights(const VoiceProfile& profile, std::function<void(const QString& error)> callback);""",
"声明 ensureWeights"),
(
"""    QVector<VoiceProfile> m_profiles;""",
"""    QVector<VoiceProfile> m_profiles;
    QString m_loadedGpt;
    QString m_loadedSovits;""",
"权重缓存成员"),
])

print("patch phase 1 done")
