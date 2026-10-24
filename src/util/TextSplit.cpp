#include "TextSplit.h"

#include <QRegularExpression>

QStringList splitForSpeech(const QString& text, int maxLen)
{
    QString cleaned = text;

    // 去掉 *动作* 与 (动作)
    cleaned.remove(QRegularExpression(QStringLiteral("\\*[^*]{0,60}\\*")));
    cleaned.remove(QRegularExpression(QStringLiteral("（[^）]{0,60}）")));
    cleaned.remove(QRegularExpression(QStringLiteral("\\([^)]{0,60}\\)")));
    cleaned.replace(QRegularExpression(QStringLiteral("[\\r\\n]+")), QStringLiteral(" "));
    cleaned = cleaned.trimmed();

    QStringList result;
    if (cleaned.isEmpty()) {
        return result;
    }

    // 一级切分：句末标点
    static const QRegularExpression sentenceEnd(QStringLiteral("(?<=[。！？!?…])"));
    const QStringList parts = cleaned.split(sentenceEnd, Qt::SkipEmptyParts);

    for (const QString& part : parts) {
        QString sentence = part.trimmed();
        if (sentence.isEmpty()) {
            continue;
        }

        // 二级切分：过长句子按逗号断开
        while (sentence.size() > maxLen) {
            int cut = -1;
            for (int i = maxLen; i > maxLen / 2; --i) {
                const QChar ch = sentence.at(i - 1);
                if (ch == QLatin1Char('，') || ch == QLatin1Char(',') || ch == QLatin1Char('；')
                    || ch == QLatin1Char(' ') || ch == QLatin1Char('、')) {
                    cut = i;
                    break;
                }
            }
            if (cut <= 0) {
                cut = maxLen;
            }
            result.append(sentence.left(cut).trimmed());
            sentence = sentence.mid(cut).trimmed();
        }

        if (!sentence.isEmpty()) {
            result.append(sentence);
        }
    }

    return result;
}

QString detectTextLang(const QString& text)
{
    static const QRegularExpression kana(QStringLiteral("[\\x{3040}-\\x{30ff}]"));
    static const QRegularExpression han(QStringLiteral("[\\x{4e00}-\\x{9fff}]"));
    static const QRegularExpression hangul(QStringLiteral("[\\x{ac00}-\\x{d7af}]"));

    if (text.contains(kana)) {
        return QStringLiteral("ja");
    }
    if (text.contains(hangul)) {
        return QStringLiteral("ko");
    }
    if (text.contains(han)) {
        return QStringLiteral("zh");
    }
    return QStringLiteral("en");
}
