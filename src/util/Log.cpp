#include "Log.h"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QTextStream>

#include <cstdio>

namespace {
QString g_filePath;

QString timestamp()
{
    return QDateTime::currentDateTime().toString(QStringLiteral("yyyy-MM-dd HH:mm:ss.zzz"));
}
} // namespace

void Log::init(const QString& filePath)
{
    g_filePath = filePath;
    const QFileInfo info(filePath);
    QDir().mkpath(info.absolutePath());

    // 简单滚动：超过 8MB 就把旧文件改名
    if (info.exists() && info.size() > 8 * 1024 * 1024) {
        const QString backup = filePath + QStringLiteral(".1");
        QFile::remove(backup);
        QFile::rename(filePath, backup);
    }
}

void Log::info(const QString& message)
{
    write(QStringLiteral("INFO"), message);
}

void Log::warn(const QString& message)
{
    write(QStringLiteral("WARN"), message);
}

void Log::error(const QString& message)
{
    write(QStringLiteral("ERROR"), message);
}

void Log::write(const QString& level, const QString& message)
{
    const QString line = QStringLiteral("[%1] [%2] %3").arg(timestamp(), level, message);

    const QByteArray utf8 = line.toUtf8();
    std::fprintf(stderr, "%s\n", utf8.constData());
    std::fflush(stderr);

    if (g_filePath.isEmpty()) {
        return;
    }

    QFile file(g_filePath);
    if (file.open(QIODevice::WriteOnly | QIODevice::Append)) {
        file.write(utf8);
        file.write("\n");
    }
}
