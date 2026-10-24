#include "HttpServer.h"

#include "../util/Log.h"

#include <QElapsedTimer>
#include <QTcpSocket>

namespace {

QString statusText(int status)
{
    switch (status) {
    case 200: return QStringLiteral("OK");
    case 204: return QStringLiteral("No Content");
    case 400: return QStringLiteral("Bad Request");
    case 404: return QStringLiteral("Not Found");
    case 405: return QStringLiteral("Method Not Allowed");
    case 500: return QStringLiteral("Internal Server Error");
    case 501: return QStringLiteral("Not Implemented");
    case 503: return QStringLiteral("Service Unavailable");
    default: return QStringLiteral("OK");
    }
}

QByteArray corsBlock(const QByteArray& origin)
{
    QByteArray out;
    if (!origin.isEmpty()) {
        out += "Access-Control-Allow-Origin: " + origin + "\r\n";
        out += "Vary: Origin\r\n";
    } else {
        out += "Access-Control-Allow-Origin: *\r\n";
    }
    out += "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n";
    out += "Access-Control-Allow-Headers: Authorization, Content-Type, X-Requested-With\r\n";
    out += "Access-Control-Max-Age: 86400\r\n";
    out += "Access-Control-Expose-Headers: Content-Type\r\n";
    return out;
}

QByteArray buildResponse(const HttpResponse& response, const QByteArray& origin)
{
    QByteArray out;
    out += "HTTP/1.1 " + QByteArray::number(response.status) + " " + statusText(response.status).toUtf8() + "\r\n";
    out += "Content-Type: " + response.contentType.toUtf8() + "\r\n";
    out += "Content-Length: " + QByteArray::number(response.body.size()) + "\r\n";
    out += "Connection: close\r\n";
    out += corsBlock(origin);
    for (auto it = response.extraHeaders.constBegin(); it != response.extraHeaders.constEnd(); ++it) {
        out += it.key().toUtf8() + ": " + it.value().toUtf8() + "\r\n";
    }
    out += "\r\n";
    out += response.body;
    return out;
}

} // namespace

/* ----------------------------- HttpStream ----------------------------- */

void HttpStream::writeHead(int status, const QByteArray& contentType)
{
    if (!socket) {
        return;
    }
    QByteArray head;
    head += "HTTP/1.1 " + QByteArray::number(status) + " " + statusText(status).toUtf8() + "\r\n";
    head += "Content-Type: " + contentType + "\r\n";
    head += "Cache-Control: no-cache\r\n";
    head += "Connection: close\r\n";
    head += "X-Accel-Buffering: no\r\n";
    head += corsBlock(origin);
    head += "\r\n";
    socket->write(head);
    socket->flush();
}

void HttpStream::writeChunk(const QByteArray& data)
{
    if (!socket || data.isEmpty()) {
        return;
    }
    socket->write(data);
    socket->flush();
}

void HttpStream::end()
{
    if (!socket) {
        return;
    }
    socket->flush();
    socket->disconnectFromHost();
}

/* ----------------------------- HttpServer ----------------------------- */

HttpServer::HttpServer(QObject* parent)
    : QObject(parent)
{
    connect(&m_server, &QTcpServer::newConnection, this, &HttpServer::onNewConnection);
}

bool HttpServer::listen(const QString& host, quint16 port)
{
    const QHostAddress address(host);
    return m_server.listen(address, port);
}

void HttpServer::setHandler(Handler handler)
{
    m_handler = std::move(handler);
}

void HttpServer::setStreamHandler(StreamHandler handler)
{
    m_streamHandler = std::move(handler);
}

quint16 HttpServer::port() const
{
    return m_server.serverPort();
}

void HttpServer::onNewConnection()
{
    while (QTcpSocket* socket = m_server.nextPendingConnection()) {
        m_clients.insert(socket, new Client());
        connect(socket, &QTcpSocket::readyRead, this, [this, socket]() { onReadyRead(socket); });
        connect(socket, &QTcpSocket::disconnected, this, [this, socket]() { onDisconnected(socket); });
    }
}

void HttpServer::onDisconnected(QTcpSocket* socket)
{
    Log::info(QStringLiteral("client disconnected"));
    if (Client* client = m_clients.take(socket)) {
        delete client;
    }
    socket->deleteLater();
}

bool HttpServer::tryParse(QTcpSocket* socket, Client* client)
{
    Q_UNUSED(socket);

    if (!client->headerDone) {
        const int headerEnd = client->buffer.indexOf("\r\n\r\n");
        if (headerEnd < 0) {
            return false;
        }

        const QByteArray headerBlock = client->buffer.left(headerEnd);
        const QList<QByteArray> lines = headerBlock.split('\n');
        if (lines.isEmpty()) {
            return false;
        }

        const QList<QByteArray> parts = lines.first().trimmed().split(' ');
        if (parts.size() < 2) {
            return false;
        }

        client->request.method = QString::fromUtf8(parts[0]);
        const QString target = QString::fromUtf8(parts[1]);
        const int question = target.indexOf(QLatin1Char('?'));
        if (question >= 0) {
            client->request.path = target.left(question);
            client->request.query = target.mid(question + 1);
        } else {
            client->request.path = target;
        }

        for (int i = 1; i < lines.size(); ++i) {
            const QByteArray line = lines.at(i).trimmed();
            const int colon = line.indexOf(':');
            if (colon <= 0) {
                continue;
            }
            const QString key = QString::fromUtf8(line.left(colon)).trimmed().toLower();
            const QString value = QString::fromUtf8(line.mid(colon + 1)).trimmed();
            client->request.headers.insert(key, value);
        }

        const QString contentLengthHeader = client->request.headers.value(QStringLiteral("content-length"));
        client->contentLength = contentLengthHeader.isEmpty() ? 0 : contentLengthHeader.toLongLong();
        client->buffer.remove(0, headerEnd + 4);
        client->headerDone = true;
    }

    if (client->buffer.size() < client->contentLength) {
        return false;
    }

    client->request.body = client->buffer.left(static_cast<int>(client->contentLength));
    client->buffer.clear();
    return true;
}

void HttpServer::onReadyRead(QTcpSocket* socket)
{
    Client* client = m_clients.value(socket, nullptr);
    if (!client || client->streaming) {
        socket->readAll(); // 已交给流处理器，丢弃多余输入
        return;
    }

    client->buffer += socket->readAll();

    if (client->buffer.size() > 8 * 1024 * 1024) {
        HttpResponse response;
        response.status = 400;
        response.body = R"({"error":{"message":"request too large"}})";
        socket->write(buildResponse(response, client->request.headers.value(QStringLiteral("origin")).toUtf8()));
        socket->flush();
        socket->disconnectFromHost();
        return;
    }

    if (!tryParse(socket, client)) {
        return;
    }

    const HttpRequest request = client->request;
    client->headerDone = false;
    client->contentLength = -1;
    client->request = HttpRequest();

    // 先给流式处理器机会接管
    if (m_streamHandler) {
        auto stream = std::make_shared<HttpStream>();
        stream->socket = socket;
        stream->origin = request.headers.value(QStringLiteral("origin")).toUtf8();
        if (m_streamHandler(request, stream)) {
            client->streaming = true;
            client->stream = stream;
            return;
        }
    }

    dispatch(socket, request);
}

void HttpServer::dispatch(QTcpSocket* socket, const HttpRequest& request)
{
    QElapsedTimer timer;
    timer.start();

    HttpResponse response;
    if (request.method == QStringLiteral("OPTIONS")) {
        response.status = 204;
        response.contentType = QStringLiteral("text/plain; charset=utf-8");
    } else if (m_handler) {
        response = m_handler(request);
    } else {
        response.status = 404;
        response.body = R"({"error":{"message":"no handler"}})";
    }

    const QByteArray origin = request.headers.value(QStringLiteral("origin")).toUtf8();
    socket->write(buildResponse(response, origin));
    socket->flush();
    socket->disconnectFromHost();

    Log::info(QStringLiteral("%1 %2 -> %3 (%4 ms)")
                  .arg(request.method, request.path)
                  .arg(response.status)
                  .arg(timer.elapsed()));
}
