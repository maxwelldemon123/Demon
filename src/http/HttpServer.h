#pragma once

#include <QByteArray>
#include <QMap>
#include <QObject>
#include <QString>
#include <QTcpServer>
#include <QPointer>
#include <QTcpSocket>

#include <memory>

#include <functional>

struct HttpRequest {
    QString method;
    QString path;
    QString query;
    QMap<QString, QString> headers; // 小写 key
    QByteArray body;
};

struct HttpResponse {
    int status = 200;
    QByteArray body;
    QString contentType = QStringLiteral("application/json; charset=utf-8");
    QMap<QString, QString> extraHeaders;
};

/**
 * 流式响应句柄：交给 SSE 这类“边说边发”的处理器。
 * 调用约定：writeHead -> writeChunk(...) * N -> end()
 */
class HttpStream {
public:
    QPointer<QTcpSocket> socket;   // 连接可能先被销毁，用 QPointer 防悬空
    QByteArray origin;

    void writeHead(int status, const QByteArray& contentType);
    void writeChunk(const QByteArray& data);
    void end();
};

/**
 * 极简 HTTP/1.1 服务器：
 *   - 解析请求行/头部/Content-Length 请求体
 *   - 普通请求：一次性响应后关闭连接
 *   - 流式请求：交给 stream handler 接管连接
 *   - 自动附加 CORS 头（酒馆页面跨源访问）
 */
class HttpServer : public QObject {
    Q_OBJECT

public:
    using Handler = std::function<HttpResponse(const HttpRequest&)>;
    using StreamHandler = std::function<bool(const HttpRequest&, const std::shared_ptr<HttpStream>&)>;

    explicit HttpServer(QObject* parent = nullptr);

    bool listen(const QString& host, quint16 port);
    void setHandler(Handler handler);
    void setStreamHandler(StreamHandler handler);
    quint16 port() const;

private:
    struct Client {
        QByteArray buffer;
        qint64 contentLength = -1;
        bool headerDone = false;
        bool streaming = false;
        std::shared_ptr<HttpStream> stream;
        HttpRequest request;
    };

    QTcpServer m_server;
    Handler m_handler;
    StreamHandler m_streamHandler;
    QMap<QTcpSocket*, Client*> m_clients;

    void onNewConnection();
    void onReadyRead(QTcpSocket* socket);
    void onDisconnected(QTcpSocket* socket);
    bool tryParse(QTcpSocket* socket, Client* client);
    void dispatch(QTcpSocket* socket, const HttpRequest& request);
};
