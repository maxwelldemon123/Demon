#pragma once

#include <QString>
#include <QStringList>

/**
 * 把模型输出切成适合逐句合成的短句：
 *   - 按 。！？!?… 换行 切
 *   - 过长的句子再按逗号切
 *   - 丢掉纯动作描写/空白
 */
QStringList splitForSpeech(const QString& text, int maxLen = 80);

/** 粗略判语种：有假名→ja，有汉字→zh，否则 en */
QString detectTextLang(const QString& text);
