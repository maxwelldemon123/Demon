#pragma once

#include <QMainWindow>
#include <QMap>

class AppController;
class QLabel;
class QListWidget;
class QStackedWidget;
class QTableWidget;
class QLineEdit;
class QSpinBox;
class QTimer;
class QPlainTextEdit;
class QPushButton;

/**
 * Demon 主窗口：仿 Electron 版的左侧导航 + 右侧面板。
 * 面板：状态 / 接口 / 启动 / 语音 / 角色 / 日志
 */
class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(AppController* controller, QWidget* parent = nullptr);

protected:
    void closeEvent(QCloseEvent* event) override;

private:
    void buildUi();
    QWidget* buildDashboard();
    QWidget* buildApiPage();
    QWidget* buildLauncherPage();
    QWidget* buildVoicePage();
    QWidget* buildCharacterPage();
    QWidget* buildLogPage();

    void refreshStatus();
    void refreshApiTable();
    void refreshVoiceTable();
    void refreshCharacterTable();
    void refreshLog();

    void saveApiTable();
    void saveVoiceTable();
    void saveCharacterTable();

    AppController* m_controller = nullptr;

    QListWidget* m_nav = nullptr;
    QStackedWidget* m_stack = nullptr;
    QLabel* m_footer = nullptr;

    // 状态页
    QLabel* m_epLabel = nullptr;
    QLabel* m_upstreamLabel = nullptr;
    QLabel* m_modelLabel = nullptr;
    QLabel* m_voiceLabel = nullptr;
    QLabel* m_queueLabel = nullptr;

    // 接口页
    QTableWidget* m_apiTable = nullptr;
    QLineEdit* m_defaultUpstream = nullptr;

    // 启动页
    QLineEdit* m_stPath = nullptr;
    QSpinBox* m_stPort = nullptr;
    QLabel* m_stState = nullptr;
    QLineEdit* m_gsvPath = nullptr;
    QLabel* m_gsvState = nullptr;

    // 语音页
    QTableWidget* m_voiceTable = nullptr;
    QLabel* m_voiceState = nullptr;

    // 角色页
    QTableWidget* m_charTable = nullptr;
    QLabel* m_charState = nullptr;

    // 日志页
    QPlainTextEdit* m_logView = nullptr;

    QTimer* m_timer = nullptr;
};
