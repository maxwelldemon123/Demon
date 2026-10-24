#pragma once

#include <QString>

/**
 * 极简日志：同时写控制台与文件。
 * 文件固定为 <exe 目录>/data/demon.log，按大小滚动（>8MB 时改名为 .1）。
 */
class Log {
public:
    static void init(const QString& filePath);
    static void info(const QString& message);
    static void warn(const QString& message);
    static void error(const QString& message);

private:
    static void write(const QString& level, const QString& message);
};
