#include "AudioPlayer.h"

#include "../util/Log.h"

#include <QAudioOutput>
#include <QMediaPlayer>
#include <QUrl>

AudioPlayer::AudioPlayer(QObject* parent)
    : QObject(parent)
    , m_player(new QMediaPlayer(this))
    , m_audio(new QAudioOutput(this))
{
    m_player->setAudioOutput(m_audio);
    m_audio->setVolume(1.0);

    connect(m_player, &QMediaPlayer::playbackStateChanged, this, [this](QMediaPlayer::PlaybackState state) {
        if (state == QMediaPlayer::PlayingState) {
            emit started();
        } else if (state == QMediaPlayer::StoppedState) {
            emit finished();
        }
    });
    connect(m_player, &QMediaPlayer::errorOccurred, this, [](QMediaPlayer::Error, const QString& errorString) {
        Log::warn(QStringLiteral("播放失败：%1").arg(errorString));
    });
}

AudioPlayer::~AudioPlayer() = default;

void AudioPlayer::playWav(const QByteArray& wav)
{
    if (wav.isEmpty()) {
        return;
    }

    m_buffer = std::make_unique<QBuffer>();
    m_buffer->setData(wav);
    m_buffer->open(QIODevice::ReadOnly);

    m_player->stop();
    m_player->setSourceDevice(m_buffer.get(), QUrl(QStringLiteral("audio/wav")));
    m_player->play();
    Log::info(QStringLiteral("开始播放 %1 KB").arg(wav.size() / 1024));
}

void AudioPlayer::setVolume(double volume)
{
    if (m_audio) {
        m_audio->setVolume(qBound(0.0, volume, 1.0));
    }
}

void AudioPlayer::stop()
{
    m_player->stop();
}

bool AudioPlayer::isPlaying() const
{
    return m_player->playbackState() == QMediaPlayer::PlayingState;
}
