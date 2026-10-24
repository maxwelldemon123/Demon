# -*- coding: utf-8 -*-
"""D4 补丁：
1) 托盘加「声线」子菜单 +「自动朗读」开关（改动写回 config.json）
2) SSE 保活（每 N 秒发 ':keep-alive'）
3) 上游按模型名路由
4) 音量配置
"""

import io, re, sys

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
    print(f"[OK] {path} ({len(pairs)} edits)")

# ---------------- Config.h ----------------
patch("src\\config\\Config.h", [(
"""struct VoiceConfig {
    QString endpoint = QStringLiteral("http://127.0.0.1:9880");
    QString profile = QStringLiteral("xiaod");
    bool autoPlay = true;
    double speed = 1.0;
};""",
"""struct VoiceConfig {
    QString endpoint = QStringLiteral("http://127.0.0.1:9880");
    QString profile = QStringLiteral("xiaod");
    bool autoPlay = true;
    double speed = 1.0;
    double volume = 1.0;
};""",
"voice.volume 字段")])

# ---------------- Config.cpp ----------------
patch("src\\config\\Config.cpp", [
(
"""        cfg.voice.speed = voice.value(QStringLiteral("speed")).toDouble(cfg.voice.speed);""",
"""        cfg.voice.speed = voice.value(QStringLiteral("speed")).toDouble(cfg.voice.speed);
        cfg.voice.volume = voice.value(QStringLiteral("volume")).toDouble(cfg.voice.volume);""",
"解析 volume"),
(
"""    voice.insert(QStringLiteral("speed"), this->voice.speed);""",
"""    voice.insert(QStringLiteral("speed"), this->voice.speed);
    voice.insert(QStringLiteral("volume"), this->voice.volume);""",
"序列化 volume"),
])

# ---------------- AudioPlayer ----------------
patch("src\\voice\\AudioPlayer.h", [(
"""    void playWav(const QByteArray& wav);""",
"""    void playWav(const QByteArray& wav);
    void setVolume(double volume);""",
"setVolume 声明")])

patch("src\\voice\\AudioPlayer.cpp", [(
"""void AudioPlayer::stop()""",
"""void AudioPlayer::setVolume(double volume)
{
    if (m_audio) {
        m_audio->setVolume(qBound(0.0, volume, 1.0));
    }
}

void AudioPlayer::stop()""",
"setVolume 实现")])

# ---------------- AppController.h ----------------
patch("src\\app\\AppController.h", [
(
"""class QMenu;""",
"""class QMenu;
class QActionGroup;""",
"前向声明 QActionGroup"),
(
"""    QAction* m_statusAction = nullptr;""",
"""    QAction* m_statusAction = nullptr;
    QMenu* m_voiceMenu = nullptr;
    QActionGroup* m_profileGroup = nullptr;
    QAction* m_autoPlayAction = nullptr;""",
"托盘成员"),
])

print("patch done")
