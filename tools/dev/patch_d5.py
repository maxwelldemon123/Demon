# -*- coding: utf-8 -*-
"""D5 补丁：稳定性 + 无控制台构建选项。"""

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
    print(f"[OK] {path} ({len(pairs)})")


# 1) CMake：可切换控制台/窗口程序
patch("CMakeLists.txt", [(
"""add_executable(demon ${DEMON_SOURCES})""",
"""# 开发时用控制台方便看日志；发布版关掉控制台（日志仍写文件）
option(DEMON_CONSOLE "Build with console window for development" OFF)

if (DEMON_CONSOLE)
    add_executable(demon ${DEMON_SOURCES})
else()
    add_executable(demon WIN32 ${DEMON_SOURCES})
endif()""",
"WIN32 选项")])

# 2) 上游中途断开也要告诉客户端
patch("src\\app\\AppController.cpp", [(
"""        if (m_reply) {
            if (m_reply->error() != QNetworkReply::NoError && m_received == 0) {
                Log::error(QStringLiteral("上游失败：%1").arg(m_reply->errorString()));
                if (m_stream) {
                    m_stream->writeChunk("data: {\\"error\\":{\\"message\\":\\"upstream failed\\"}}\\n\\n");
                    m_stream->writeChunk("data: [DONE]\\n\\n");
                }
            } else if (m_received == 0 && m_stream) {
                m_stream->writeChunk("data: [DONE]\\n\\n");
            }
        }""",
"""        if (m_reply && m_reply->error() != QNetworkReply::NoError) {
            // 无论是首包就失败还是中途断开，都要让客户端收到明确的结束标记，
            // 否则酒馆会一直转圈等 token。
            Log::error(QStringLiteral("上游失败：%1（已收到 %2 字节）")
                           .arg(m_reply->errorString())
                           .arg(m_received));
            if (m_stream) {
                const QByteArray payload = QStringLiteral(
                    "{\\"error\\":{\\"message\\":\\"上游中断：%1\\"}}")
                                               .arg(m_reply->errorString())
                                               .toUtf8();
                m_stream->writeChunk("data: " + payload + "\\n\\n");
                m_stream->writeChunk("data: [DONE]\\n\\n");
            }
        } else if (m_received == 0 && m_stream) {
            m_stream->writeChunk("data: [DONE]\\n\\n");
        }""",
"中途断开处理"),
])

# 3) 端口占用给用户明确提示
patch("src\\app\\AppController.cpp", [
(
"""#include <QJsonDocument>""",
"""#include <QJsonDocument>
#include <QMessageBox>""",
"include QMessageBox"),
(
"""    if (!m_server->listen(m_config.host, m_config.port)) {
        Log::error(QStringLiteral("监听失败：%1:%2（端口可能被占用）").arg(m_config.host).arg(m_config.port));
        return false;
    }""",
"""    if (!m_server->listen(m_config.host, m_config.port)) {
        const QString message = QStringLiteral("无法监听 %1:%2，端口可能被占用。\\n\\n"
                                               "请关闭占用该端口的程序，或修改 config.json 里的 listen.port。")
                                    .arg(m_config.host)
                                    .arg(m_config.port);
        Log::error(message);
        QMessageBox::critical(nullptr, QStringLiteral("Demon 启动失败"), message);
        return false;
    }""",
"端口占用提示"),
])

print("patch d5 done")
