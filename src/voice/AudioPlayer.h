#pragma once

#include <QBuffer>
#include <QByteArray>
#include <QObject>

#include <memory>

class QMediaPlayer;
class QAudioOutput;

/**
 * WAV 播放器：把内存里的 wav 交给 QMediaPlayer 播放。
 * 没有音频设备时只记日志，不影响主流程。
 */
class AudioPlayer : public QObject {
    Q_OBJECT

public:
    explicit AudioPlayer(QObject* parent = nullptr);
    ~AudioPlayer() override;

    void playWav(const QByteArray& wav);
    void setVolume(double volume);
    void stop();
    bool isPlaying() const;

signals:
    void started();
    void finished();

private:
    QMediaPlayer* m_player = nullptr;
    QAudioOutput* m_audio = nullptr;
    std::unique_ptr<QBuffer> m_buffer;
};
