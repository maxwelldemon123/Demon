#include "MainWindow.h"

#include "app/AppController.h"
#include "util/Log.h"

#include <QClipboard>
#include <QGuiApplication>
#include <QScrollBar>
#include <QAbstractItemView>
#include <QCheckBox>
#include <QCloseEvent>
#include <QComboBox>
#include <QCoreApplication>
#include <QDesktopServices>
#include <QDir>
#include <QFile>
#include <QFileDialog>
#include <QFormLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMessageBox>
#include <QPlainTextEdit>
#include <QProcess>
#include <QPushButton>
#include <QSpinBox>
#include <QStackedWidget>
#include <QTableWidget>
#include <QTimer>
#include <QUrl>
#include <QVBoxLayout>

namespace {

const char* kStyle = R"(
QWidget#sidebar { background:#17171f; }
QLabel#brand { color:#cbb8ff; font-size:20px; font-weight:700; padding:18px 14px 10px 16px; }
QListWidget#nav { background:transparent; border:none; color:#a9a9bd; font-size:13px; outline:none; }
QListWidget#nav::item { padding:11px 16px; border-left:3px solid transparent; }
QListWidget#nav::item:selected { color:#ffffff; background:#232333; border-left:3px solid #8b6cff; }
QListWidget#nav::item:hover { color:#ffffff; }
QWidget#content { background:#1e1e28; }
QLabel#pageTitle { color:#ffffff; font-size:17px; font-weight:600; }
QLabel#hint { color:#8d8da6; font-size:12px; }
QLabel#footer { color:#8d8da6; font-size:12px; padding:6px 12px; background:#17171f; }
QGroupBox { color:#c9c9de; border:1px solid #2f2f42; border-radius:8px; margin-top:12px; padding-top:8px; }
QGroupBox::title { subcontrol-origin: margin; left:12px; padding:0 4px; }
QLabel { color:#d6d6e6; }
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTableWidget {
    background:#262635; color:#e6e6f2; border:1px solid #34344a; border-radius:5px; padding:4px 6px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border:1px solid #8b6cff; }
QPushButton { background:#2c2c3f; color:#e6e6f2; border:1px solid #3a3a52; border-radius:6px; padding:6px 12px; }
QPushButton:hover { background:#3a3a52; }
QPushButton#primary { background:#7350ff; border:1px solid #8b6cff; }
QPushButton#primary:hover { background:#8b6cff; }
QHeaderView::section { background:#262635; color:#b9b9cf; border:none; padding:5px; }
QTableWidget::item { padding:3px; }
)";

QTableWidgetItem* item(const QString& text)
{
    auto* it = new QTableWidgetItem(text);
    return it;
}

} // namespace


namespace {

/** 打开浏览器（交给 controller，cmd start 优先） */
bool openInBrowser(AppController* controller, const QString& url)
{
    return controller->openExternalUrl(url);
}

} // namespace

MainWindow::MainWindow(AppController* controller, QWidget* parent)
    : QMainWindow(parent)
    , m_controller(controller)
{
    setWindowTitle(QStringLiteral("Demon"));
    resize(1000, 660);
    setStyleSheet(QString::fromUtf8(kStyle));
    buildUi();

    connect(m_controller, &AppController::uiDirty, this, [this]() { refreshStatus(); });

    m_timer = new QTimer(this);
    m_timer->setInterval(1500);
    connect(m_timer, &QTimer::timeout, this, [this]() {
        const bool st = AppController::portOpen(static_cast<quint16>(m_stPort->value()));
        const bool gsv = AppController::portOpen(9880);
        m_stState->setText(st ? QStringLiteral("● 运行中") : QStringLiteral("○ 未运行"));
        m_stState->setStyleSheet(st ? "color:#4ade80;" : "color:#8d8da6;");
        m_gsvState->setText(gsv ? QStringLiteral("● 运行中") : QStringLiteral("○ 未运行"));
        m_gsvState->setStyleSheet(gsv ? "color:#4ade80;" : "color:#8d8da6;");
    });
    m_timer->start();


    refreshStatus();
    refreshApiTable();
    refreshVoiceTable();
    refreshCharacterTable();
}

void MainWindow::buildUi()
{
    auto* central = new QWidget(this);
    auto* root = new QHBoxLayout(central);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);

    // 左侧导航
    auto* side = new QWidget(central);
    side->setObjectName("sidebar");
    side->setFixedWidth(176);
    auto* sideLayout = new QVBoxLayout(side);
    sideLayout->setContentsMargins(0, 0, 0, 0);
    sideLayout->setSpacing(0);

    auto* brand = new QLabel(QStringLiteral("Demon"), side);
    brand->setObjectName("brand");
    sideLayout->addWidget(brand);

    m_nav = new QListWidget(side);
    m_nav->setObjectName("nav");
    m_nav->addItems({QStringLiteral("状态"), QStringLiteral("接口"), QStringLiteral("启动"),
                     QStringLiteral("语音"), QStringLiteral("角色"), QStringLiteral("日志")});
    sideLayout->addWidget(m_nav, 1);

    root->addWidget(side);

    // 右侧内容
    auto* contentWrap = new QWidget(central);
    contentWrap->setObjectName("content");
    auto* contentLayout = new QVBoxLayout(contentWrap);
    contentLayout->setContentsMargins(0, 0, 0, 0);
    contentLayout->setSpacing(0);

    m_stack = new QStackedWidget(contentWrap);
    m_stack->addWidget(buildDashboard());
    m_stack->addWidget(buildApiPage());
    m_stack->addWidget(buildLauncherPage());
    m_stack->addWidget(buildVoicePage());
    m_stack->addWidget(buildCharacterPage());
    m_stack->addWidget(buildLogPage());
    contentLayout->addWidget(m_stack, 1);

    m_footer = new QLabel(contentWrap);
    m_footer->setObjectName("footer");
    contentLayout->addWidget(m_footer);

    root->addWidget(contentWrap, 1);
    setCentralWidget(central);

    connect(m_nav, &QListWidget::currentRowChanged, this, [this](int row) {
        m_stack->setCurrentIndex(row);
        Log::info(QStringLiteral("导航切换到第 %1 页（stack=%2）").arg(row).arg(m_stack->currentIndex()));
    });
    m_nav->setCurrentRow(0);
}

QWidget* MainWindow::buildDashboard()
{
    auto* page = new QWidget;
    auto* layout = new QVBoxLayout(page);
    layout->setContentsMargins(22, 18, 22, 12);

    auto* title = new QLabel(QStringLiteral("运行状态"));
    title->setObjectName("pageTitle");
    layout->addWidget(title);

    auto* box = new QGroupBox(QStringLiteral("引擎"));
    auto* form = new QFormLayout(box);
    m_epLabel = new QLabel;
    m_upstreamLabel = new QLabel;
    m_modelLabel = new QLabel;
    m_voiceLabel = new QLabel;
    m_queueLabel = new QLabel;
    for (QLabel* l : {m_epLabel, m_upstreamLabel, m_modelLabel, m_voiceLabel, m_queueLabel}) {
        l->setTextInteractionFlags(Qt::TextSelectableByMouse);
    }
    form->addRow(QStringLiteral("监听地址"), m_epLabel);
    form->addRow(QStringLiteral("当前上游"), m_upstreamLabel);
    form->addRow(QStringLiteral("对外模型"), m_modelLabel);
    form->addRow(QStringLiteral("默认声线"), m_voiceLabel);
    form->addRow(QStringLiteral("语音队列"), m_queueLabel);
    layout->addWidget(box);

    auto* buttons = new QHBoxLayout;
    auto* copy = new QPushButton(QStringLiteral("复制接口地址"));
    copy->setObjectName("primary");
    auto* log = new QPushButton(QStringLiteral("打开日志"));
    auto* cfg = new QPushButton(QStringLiteral("配置目录"));
    auto* reload = new QPushButton(QStringLiteral("重载配置"));
    buttons->addWidget(copy);
    buttons->addWidget(log);
    buttons->addWidget(cfg);
    buttons->addWidget(reload);
    buttons->addStretch();
    layout->addLayout(buttons);
    layout->addStretch();

    connect(copy, &QPushButton::clicked, this, [this, copy]() {
        const QString url = QStringLiteral("http://%1:%2/v1")
                                .arg(m_controller->config().host)
                                .arg(m_controller->config().port);
        QGuiApplication::clipboard()->setText(url);
        copy->setText(QStringLiteral("已复制 ✓"));
        QTimer::singleShot(1200, copy, [copy]() { copy->setText(QStringLiteral("复制接口地址")); });
    });
    connect(log, &QPushButton::clicked, m_controller, &AppController::openLogFile);
    connect(cfg, &QPushButton::clicked, m_controller, &AppController::openConfigFolder);
    connect(reload, &QPushButton::clicked, m_controller, &AppController::reloadConfig);

    return page;
}

QWidget* MainWindow::buildApiPage()
{
    auto* page = new QWidget;
    auto* layout = new QVBoxLayout(page);
    layout->setContentsMargins(22, 18, 22, 12);

    auto* title = new QLabel(QStringLiteral("接口 / 上游"));
    title->setObjectName("pageTitle");
    layout->addWidget(title);

    auto* hint = new QLabel(QStringLiteral("酒馆里的自定义端点填：http://127.0.0.1:8790/v1，模型名写对外模型（默认 demon）"));
    hint->setObjectName("hint");
    layout->addWidget(hint);

    m_apiTable = new QTableWidget(0, 4);
    m_apiTable->setHorizontalHeaderLabels({QStringLiteral("ID"), QStringLiteral("地址（到 /v1）"),
                                           QStringLiteral("模型"), QStringLiteral("密钥")});
    m_apiTable->horizontalHeader()->setStretchLastSection(true);
    m_apiTable->horizontalHeader()->setSectionResizeMode(1, QHeaderView::Stretch);
    m_apiTable->verticalHeader()->setVisible(false);
    m_apiTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    layout->addWidget(m_apiTable, 1);

    auto* row = new QHBoxLayout;
    auto* add = new QPushButton(QStringLiteral("添加"));
    auto* remove = new QPushButton(QStringLiteral("删除选中"));
    auto* save = new QPushButton(QStringLiteral("保存并生效"));
    save->setObjectName("primary");
    row->addWidget(add);
    row->addWidget(remove);
    row->addWidget(save);
    row->addSpacing(16);
    row->addWidget(new QLabel(QStringLiteral("默认上游")));
    m_defaultUpstream = new QLineEdit;
    m_defaultUpstream->setFixedWidth(140);
    row->addWidget(m_defaultUpstream);
    row->addStretch();
    layout->addLayout(row);

    connect(add, &QPushButton::clicked, this, [this]() {
        const int rowIndex = m_apiTable->rowCount();
        m_apiTable->insertRow(rowIndex);
        m_apiTable->setItem(rowIndex, 0, item(QStringLiteral("upstream%1").arg(rowIndex + 1)));
        m_apiTable->setItem(rowIndex, 1, item(QStringLiteral("http://127.0.0.1:8080/v1")));
        m_apiTable->setItem(rowIndex, 2, item(QStringLiteral("local-model")));
        m_apiTable->setItem(rowIndex, 3, item(QString()));
    });
    connect(remove, &QPushButton::clicked, this, [this]() {
        const int rowIndex = m_apiTable->currentRow();
        if (rowIndex >= 0) {
            m_apiTable->removeRow(rowIndex);
        }
    });
    connect(save, &QPushButton::clicked, this, [this]() { saveApiTable(); });

    return page;
}

QWidget* MainWindow::buildLauncherPage()
{
    auto* page = new QWidget;
    auto* layout = new QVBoxLayout(page);
    layout->setContentsMargins(22, 18, 22, 12);

    auto* title = new QLabel(QStringLiteral("启动器"));
    title->setObjectName("pageTitle");
    layout->addWidget(title);

    // 酒馆
    auto* stBox = new QGroupBox(QStringLiteral("SillyTavern"));
    auto* stLayout = new QGridLayout(stBox);
    stLayout->addWidget(new QLabel(QStringLiteral("安装目录")), 0, 0);
    m_stPath = new QLineEdit;
    m_stPath->setText(m_controller->config().launcher.stPath);
    stLayout->addWidget(m_stPath, 0, 1);
    auto* stBrowse = new QPushButton(QStringLiteral("浏览…"));
    stLayout->addWidget(stBrowse, 0, 2);
    stLayout->addWidget(new QLabel(QStringLiteral("端口")), 1, 0);
    m_stPort = new QSpinBox;
    m_stPort->setRange(1024, 65535);
    m_stPort->setFixedWidth(110);
    m_stPort->setValue(m_controller->config().launcher.stPort);
    stLayout->addWidget(m_stPort, 1, 1);
    m_stState = new QLabel(QStringLiteral("○ 未运行"));
    stLayout->addWidget(m_stState, 1, 2);
    auto* stButtons = new QHBoxLayout;
    auto* stStart = new QPushButton(QStringLiteral("启动酒馆"));
    stStart->setObjectName("primary");
    auto* stStop = new QPushButton(QStringLiteral("停止酒馆"));
    auto* stOpen = new QPushButton(QStringLiteral("打开页面"));
    stButtons->addWidget(stStart);
    stButtons->addWidget(stStop);
    stButtons->addWidget(stOpen);
    stButtons->addStretch();
    stLayout->addLayout(stButtons, 2, 0, 1, 3);
    layout->addWidget(stBox);

    // 语音
    auto* gsvBox = new QGroupBox(QStringLiteral("GPT-SoVITS 语音服务（api_v2）"));
    auto* gsvLayout = new QGridLayout(gsvBox);
    gsvLayout->addWidget(new QLabel(QStringLiteral("安装目录")), 0, 0);
    m_gsvPath = new QLineEdit;
    m_gsvPath->setText(m_controller->config().launcher.gsvPath);
    gsvLayout->addWidget(m_gsvPath, 0, 1);
    auto* gsvBrowse = new QPushButton(QStringLiteral("浏览…"));
    gsvLayout->addWidget(gsvBrowse, 0, 2);
    gsvLayout->addWidget(new QLabel(QStringLiteral("状态")), 1, 0);
    m_gsvState = new QLabel(QStringLiteral("○ 未运行"));
    gsvLayout->addWidget(m_gsvState, 1, 1);
    auto* gsvButtons = new QHBoxLayout;
    auto* gsvStart = new QPushButton(QStringLiteral("启动语音服务"));
    gsvStart->setObjectName("primary");
    auto* gsvStop = new QPushButton(QStringLiteral("停止语音服务"));
    auto* gsvFolder = new QPushButton(QStringLiteral("打开目录"));
    gsvButtons->addWidget(gsvStart);
    gsvButtons->addWidget(gsvStop);
    gsvButtons->addWidget(gsvFolder);
    gsvButtons->addStretch();
    gsvLayout->addLayout(gsvButtons, 2, 0, 1, 3);
    layout->addWidget(gsvBox);

    auto* hint = new QLabel(QStringLiteral("提示：启动脚本分别是 <酒馆目录>\\Start.bat 与 <语音目录>\\start-api-v2pro.bat。"
                                           "语音服务首次加载模型约 20~60 秒。"));
    hint->setObjectName("hint");
    hint->setWordWrap(true);
    layout->addWidget(hint);
    layout->addStretch();

    connect(stBrowse, &QPushButton::clicked, this, [this]() {
        const QString dir = QFileDialog::getExistingDirectory(this, QStringLiteral("选择 SillyTavern 目录"), m_stPath->text());
        if (!dir.isEmpty()) {
            m_stPath->setText(dir);
        }
    });
    connect(gsvBrowse, &QPushButton::clicked, this, [this]() {
        const QString dir = QFileDialog::getExistingDirectory(this, QStringLiteral("选择 GPT-SoVITS 目录"), m_gsvPath->text());
        if (!dir.isEmpty()) {
            m_gsvPath->setText(dir);
        }
    });
    connect(stStart, &QPushButton::clicked, this, [this]() {
        auto& cfg = m_controller->mutableConfig();
        cfg.launcher.stPath = m_stPath->text().trimmed();
        cfg.launcher.stPort = m_stPort->value();
        m_controller->saveConfig();
        QString error;
        if (!m_controller->startSillyTavern(&error)) {
            QMessageBox::warning(this, QStringLiteral("启动酒馆"), error);
            return;
        }
        if (AppController::portOpen(static_cast<quint16>(m_stPort->value()))) {
            // 已经在跑：Start.bat 不会再开浏览器，这里给个手动入口
            m_controller->openInEdge(QStringLiteral("http://127.0.0.1:%1/").arg(m_stPort->value()));
            Log::info(QStringLiteral("酒馆已在运行，打开页面"));
        } else {
            // 未运行：只拉起 Start.bat，浏览器由它自己打开
            Log::info(QStringLiteral("已启动酒馆（浏览器由 Start.bat 打开）"));
        }
    });
    connect(stStop, &QPushButton::clicked, this, [this]() {
        QString error;
        if (!m_controller->stopSillyTavern(&error)) {
            QMessageBox::information(this, QStringLiteral("停止酒馆"), error);
        }
    });
    connect(stOpen, &QPushButton::clicked, this, [this]() {
        openInBrowser(m_controller, QStringLiteral("http://127.0.0.1:%1/").arg(m_stPort->value()));
    });
    connect(gsvStart, &QPushButton::clicked, this, [this]() {
        auto& cfg = m_controller->mutableConfig();
        cfg.launcher.gsvPath = m_gsvPath->text().trimmed();
        m_controller->saveConfig();
        QString error;
        if (!m_controller->startVoiceService(&error)) {
            QMessageBox::warning(this, QStringLiteral("启动语音服务"), error);
        }
    });
    connect(gsvStop, &QPushButton::clicked, this, [this]() {
        QString error;
        if (!m_controller->stopVoiceService(&error)) {
            QMessageBox::information(this, QStringLiteral("停止语音服务"), error);
        }
    });
    connect(gsvFolder, &QPushButton::clicked, this, [this]() {
        QDesktopServices::openUrl(QUrl::fromLocalFile(m_gsvPath->text().trimmed()));
    });

    return page;
}

QWidget* MainWindow::buildVoicePage()
{
    auto* page = new QWidget;
    auto* layout = new QVBoxLayout(page);
    layout->setContentsMargins(22, 18, 22, 12);

    auto* title = new QLabel(QStringLiteral("语音档案"));
    title->setObjectName("pageTitle");
    layout->addWidget(title);

    auto* hint = new QLabel(QStringLiteral("参考音频与权重路径相对 GPT-SoVITS 目录；也可写绝对路径。切换声线时会自动切权重。"));
    hint->setObjectName("hint");
    hint->setWordWrap(true);
    layout->addWidget(hint);

    m_voiceTable = new QTableWidget(0, 6);
    m_voiceTable->setHorizontalHeaderLabels({QStringLiteral("ID"), QStringLiteral("名称"),
                                             QStringLiteral("参考音频"), QStringLiteral("GPT 权重"),
                                             QStringLiteral("SoVITS 权重"), QStringLiteral("提示文本")});
    m_voiceTable->horizontalHeader()->setStretchLastSection(true);
    m_voiceTable->horizontalHeader()->setSectionResizeMode(2, QHeaderView::Stretch);
    m_voiceTable->verticalHeader()->setVisible(false);
    m_voiceTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    layout->addWidget(m_voiceTable, 1);

    auto* row = new QHBoxLayout;
    auto* add = new QPushButton(QStringLiteral("添加"));
    auto* remove = new QPushButton(QStringLiteral("删除选中"));
    auto* save = new QPushButton(QStringLiteral("保存"));
    save->setObjectName("primary");
    auto* test = new QPushButton(QStringLiteral("试听选中"));
    auto* setDefault = new QPushButton(QStringLiteral("设为默认"));
    row->addWidget(add);
    row->addWidget(remove);
    row->addWidget(save);
    row->addSpacing(12);
    row->addWidget(test);
    row->addWidget(setDefault);
    row->addStretch();
    layout->addLayout(row);

    m_voiceState = new QLabel;
    m_voiceState->setObjectName("hint");
    layout->addWidget(m_voiceState);

    connect(add, &QPushButton::clicked, this, [this]() {
        const int rowIndex = m_voiceTable->rowCount();
        m_voiceTable->insertRow(rowIndex);
        m_voiceTable->setItem(rowIndex, 0, item(QStringLiteral("voice%1").arg(rowIndex + 1)));
        m_voiceTable->setItem(rowIndex, 1, item(QStringLiteral("新声线")));
        m_voiceTable->setItem(rowIndex, 2, item(QStringLiteral("refs/xiaod.wav")));
        m_voiceTable->setItem(rowIndex, 3, item(QString()));
        m_voiceTable->setItem(rowIndex, 4, item(QString()));
        m_voiceTable->setItem(rowIndex, 5, item(QString()));
    });
    connect(remove, &QPushButton::clicked, this, [this]() {
        const int rowIndex = m_voiceTable->currentRow();
        if (rowIndex >= 0) {
            m_voiceTable->removeRow(rowIndex);
        }
    });
    connect(save, &QPushButton::clicked, this, [this]() { saveVoiceTable(); });
    connect(test, &QPushButton::clicked, this, [this]() {
        const int rowIndex = m_voiceTable->currentRow();
        if (rowIndex < 0) {
            return;
        }
        m_controller->testVoice(m_voiceTable->item(rowIndex, 0)->text().trimmed());
    });
    connect(setDefault, &QPushButton::clicked, this, [this]() {
        const int rowIndex = m_voiceTable->currentRow();
        if (rowIndex < 0) {
            return;
        }
        m_controller->setDefaultProfile(m_voiceTable->item(rowIndex, 0)->text().trimmed());
        refreshStatus();
    });

    return page;
}

QWidget* MainWindow::buildCharacterPage()
{
    auto* page = new QWidget;
    auto* layout = new QVBoxLayout(page);
    layout->setContentsMargins(22, 18, 22, 12);

    auto* title = new QLabel(QStringLiteral("角色声线"));
    title->setObjectName("pageTitle");
    layout->addWidget(title);

    auto* hint = new QLabel(QStringLiteral("给每个角色卡指定声线；聊天时 Demon 会在请求里识别角色名并自动用对应声线。未指定的角色用默认声线。"));
    hint->setObjectName("hint");
    hint->setWordWrap(true);
    layout->addWidget(hint);

    m_charTable = new QTableWidget(0, 3);
    m_charTable->setHorizontalHeaderLabels({QStringLiteral("角色卡"), QStringLiteral("声线"), QStringLiteral("来源")});
    m_charTable->horizontalHeader()->setStretchLastSection(true);
    m_charTable->verticalHeader()->setVisible(false);
    layout->addWidget(m_charTable, 1);

    auto* row = new QHBoxLayout;
    auto* refresh = new QPushButton(QStringLiteral("刷新角色列表"));
    auto* save = new QPushButton(QStringLiteral("保存绑定"));
    save->setObjectName("primary");
    row->addWidget(refresh);
    row->addWidget(save);
    row->addStretch();
    layout->addLayout(row);

    m_charState = new QLabel;
    m_charState->setObjectName("hint");
    layout->addWidget(m_charState);

    connect(refresh, &QPushButton::clicked, this, [this]() { refreshCharacterTable(); });
    connect(save, &QPushButton::clicked, this, [this]() { saveCharacterTable(); });

    return page;
}

QWidget* MainWindow::buildLogPage()
{
    auto* page = new QWidget;
    auto* layout = new QVBoxLayout(page);
    layout->setContentsMargins(22, 18, 22, 12);

    auto* title = new QLabel(QStringLiteral("日志"));
    title->setObjectName("pageTitle");
    layout->addWidget(title);

    m_logView = new QPlainTextEdit;
    m_logView->setReadOnly(true);
    layout->addWidget(m_logView, 1);

    auto* row = new QHBoxLayout;
    auto* refresh = new QPushButton(QStringLiteral("刷新"));
    auto* open = new QPushButton(QStringLiteral("用记事本打开"));
    row->addWidget(refresh);
    row->addWidget(open);
    row->addStretch();
    layout->addLayout(row);

    connect(refresh, &QPushButton::clicked, this, [this]() { refreshLog(); });
    connect(open, &QPushButton::clicked, m_controller, &AppController::openLogFile);

    return page;
}

void MainWindow::refreshStatus()
{
    const Config& cfg = m_controller->config();
    if (m_epLabel) {
        m_epLabel->setText(QStringLiteral("http://%1:%2").arg(cfg.host).arg(cfg.port));
        const UpstreamConfig* up = nullptr;
        for (const UpstreamConfig& u : cfg.upstreams) {
            if (u.id == cfg.effectiveUpstreamId()) {
                up = &u;
                break;
            }
        }
        m_upstreamLabel->setText(up ? QStringLiteral("%1（%2）").arg(up->baseUrl, up->model)
                                    : QStringLiteral("未配置"));
        m_modelLabel->setText(cfg.modelId);
        m_voiceLabel->setText(cfg.voice.profile);
        m_queueLabel->setText(QStringLiteral("空闲"));
    }
    m_footer->setText(QStringLiteral("接口 http://%1:%2   ·   上游 %3   ·   语音 %4   ·   角色绑定 %5")
                          .arg(cfg.host)
                          .arg(cfg.port)
                          .arg(cfg.effectiveUpstreamId())
                          .arg(cfg.voice.endpoint)
                          .arg(cfg.characterVoices.size()));
}

void MainWindow::refreshApiTable()
{
    const Config& cfg = m_controller->config();
    m_apiTable->setRowCount(0);
    for (const UpstreamConfig& u : cfg.upstreams) {
        const int row = m_apiTable->rowCount();
        m_apiTable->insertRow(row);
        m_apiTable->setItem(row, 0, item(u.id));
        m_apiTable->setItem(row, 1, item(u.baseUrl));
        m_apiTable->setItem(row, 2, item(u.model));
        m_apiTable->setItem(row, 3, item(u.apiKey));
    }
    m_defaultUpstream->setText(cfg.effectiveUpstreamId());
}

void MainWindow::saveApiTable()
{
    QVector<UpstreamConfig> ups;
    for (int row = 0; row < m_apiTable->rowCount(); ++row) {
        auto text = [this, row](int col) {
            QTableWidgetItem* it = m_apiTable->item(row, col);
            return it ? it->text().trimmed() : QString();
        };
        UpstreamConfig u;
        u.id = text(0);
        u.baseUrl = text(1);
        u.model = text(2);
        u.apiKey = text(3);
        if (!u.id.isEmpty() && !u.baseUrl.isEmpty()) {
            ups.append(u);
        }
    }
    auto& cfg = m_controller->mutableConfig();
    cfg.upstreams = ups;
    cfg.defaultUpstreamId = m_defaultUpstream->text().trimmed();
    m_controller->saveConfig();
    m_controller->reloadConfig();
    refreshApiTable();
    refreshStatus();
}

void MainWindow::refreshVoiceTable()
{
    const Config& cfg = m_controller->config();
    m_voiceTable->setRowCount(0);
    for (const VoiceProfileConfig& p : cfg.voiceProfiles) {
        const int row = m_voiceTable->rowCount();
        m_voiceTable->insertRow(row);
        m_voiceTable->setItem(row, 0, item(p.id));
        m_voiceTable->setItem(row, 1, item(p.name));
        QString refShow = p.refAudio;
        const QString baseDir = QCoreApplication::applicationDirPath() + QLatin1Char('/');
        if (refShow.startsWith(baseDir)) {
            refShow = refShow.mid(baseDir.size());
        }
        m_voiceTable->setItem(row, 2, item(refShow));
        m_voiceTable->setItem(row, 3, item(p.gptWeights));
        m_voiceTable->setItem(row, 4, item(p.sovitsWeights));
        m_voiceTable->setItem(row, 5, item(p.promptText));
    }
    m_voiceTable->setColumnWidth(0, 150);
    m_voiceTable->setColumnWidth(1, 150);
    m_voiceTable->setColumnWidth(2, 260);
    m_voiceTable->setColumnWidth(3, 210);
    m_voiceTable->setColumnWidth(4, 220);
    m_voiceState->setText(QStringLiteral("共 %1 条声线，默认：%2").arg(cfg.voiceProfiles.size()).arg(cfg.voice.profile));
}

void MainWindow::saveVoiceTable()
{
    QVector<VoiceProfileConfig> profiles;
    for (int row = 0; row < m_voiceTable->rowCount(); ++row) {
        auto text = [this, row](int col) {
            QTableWidgetItem* it = m_voiceTable->item(row, col);
            return it ? it->text().trimmed() : QString();
        };
        VoiceProfileConfig p;
        p.id = text(0);
        p.name = text(1);
        p.refAudio = text(2);
        p.gptWeights = text(3);
        p.sovitsWeights = text(4);
        p.promptText = text(5);
        if (!p.id.isEmpty()) {
            profiles.append(p);
        }
    }
    auto& cfg = m_controller->mutableConfig();
    cfg.voiceProfiles = profiles;
    m_controller->saveConfig();
    m_controller->reloadConfig();
    refreshVoiceTable();
    refreshCharacterTable();
    refreshStatus();
}

void MainWindow::refreshCharacterTable()
{
    const Config& cfg = m_controller->config();
    const QStringList characters = m_controller->listCharacters();

    QStringList profileIds;
    for (const VoiceProfileConfig& p : cfg.voiceProfiles) {
        profileIds.append(p.id);
    }

    m_charTable->setRowCount(0);
    for (const QString& name : characters) {
        const int row = m_charTable->rowCount();
        m_charTable->insertRow(row);
        m_charTable->setItem(row, 0, item(name));

        auto* combo = new QComboBox;
        combo->addItem(QStringLiteral("（默认）"), QString());
        for (const QString& id : profileIds) {
            combo->addItem(id, id);
        }
        const QString bound = cfg.characterVoices.value(name);
        const int index = combo->findData(bound);
        if (index >= 0) {
            combo->setCurrentIndex(index);
        }
        m_charTable->setCellWidget(row, 1, combo);

        m_charTable->setItem(row, 2, item(QStringLiteral("角色卡目录")));
    }
    m_charState->setText(QStringLiteral("目录：%1（%2 个角色）")
                             .arg(m_controller->effectiveCharactersDir())
                             .arg(characters.size()));
}

void MainWindow::saveCharacterTable()
{
    auto& cfg = m_controller->mutableConfig();
    cfg.characterVoices.clear();
    for (int row = 0; row < m_charTable->rowCount(); ++row) {
        QTableWidgetItem* nameItem = m_charTable->item(row, 0);
        auto* combo = qobject_cast<QComboBox*>(m_charTable->cellWidget(row, 1));
        if (!nameItem || !combo) {
            continue;
        }
        const QString profile = combo->currentData().toString();
        if (!profile.isEmpty()) {
            cfg.characterVoices.insert(nameItem->text(), profile);
        }
    }
    m_controller->saveConfig();
    refreshStatus();
    m_charState->setText(QStringLiteral("已保存 %1 条绑定").arg(cfg.characterVoices.size()));
}

void MainWindow::refreshLog()
{
    const QString path = QCoreApplication::applicationDirPath() + QStringLiteral("/data/demon.log");
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) {
        m_logView->setPlainText(QStringLiteral("打不开日志：%1").arg(path));
        return;
    }
    const QByteArray all = file.readAll();
    const int keep = 64 * 1024;
    m_logView->setPlainText(QString::fromUtf8(all.size() > keep ? all.right(keep) : all));
    m_logView->verticalScrollBar()->setValue(m_logView->verticalScrollBar()->maximum());
}

void MainWindow::closeEvent(QCloseEvent* event)
{
    event->accept();
    QCoreApplication::quit();
}
