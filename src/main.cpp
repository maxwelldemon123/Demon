#include "app/AppController.h"

#include <QApplication>
#include <QIcon>
#include <QDir>
#include <QFile>

int main(int argc, char** argv)
{
    QApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("Demon"));
    app.setApplicationVersion(QStringLiteral("0.1.0"));
    // 托盘程序：关掉最后一个窗口不退出
    app.setQuitOnLastWindowClosed(false);

    // 窗口/任务栏图标：优先用同目录的 demon.ico
    const QString iconPath = QCoreApplication::applicationDirPath() + QStringLiteral("/demon.ico");
    if (QFile::exists(iconPath)) {
        app.setWindowIcon(QIcon(iconPath));
    }

    AppController controller;
    if (!controller.start()) {
        return 1;
    }

    return app.exec();
}
