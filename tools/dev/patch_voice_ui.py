# -*- coding: utf-8 -*-
"""语音页显示优化 + 角色绑定端到端验证前的准备。"""

import io

P = r"E:\dshwork\Demon\src\ui\MainWindow.cpp"
t = io.open(P, encoding="utf-8").read()

old = """        m_voiceTable->setItem(row, 2, item(p.refAudio));"""
new = """        QString refShow = p.refAudio;
        const QString baseDir = QCoreApplication::applicationDirPath() + QLatin1Char('/');
        if (refShow.startsWith(baseDir)) {
            refShow = refShow.mid(baseDir.size());
        }
        m_voiceTable->setItem(row, 2, item(refShow));"""
if old in t:
    t = t.replace(old, new)
    print("[OK] 参考音频相对显示")

old2 = """    m_voiceState->setText(QStringLiteral("共 %1 条声线，默认：%2").arg(cfg.voiceProfiles.size()).arg(cfg.voice.profile));"""
new2 = """    m_voiceTable->setColumnWidth(0, 150);
    m_voiceTable->setColumnWidth(1, 150);
    m_voiceTable->setColumnWidth(2, 260);
    m_voiceTable->setColumnWidth(3, 210);
    m_voiceTable->setColumnWidth(4, 220);
    m_voiceState->setText(QStringLiteral("共 %1 条声线，默认：%2").arg(cfg.voiceProfiles.size()).arg(cfg.voice.profile));"""
if old2 in t:
    t = t.replace(old2, new2)
    print("[OK] 列宽")

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("done")
