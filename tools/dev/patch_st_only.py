# -*- coding: utf-8 -*-
"""去掉 Demon 启动酒馆后自动开浏览器的逻辑，完全交给 Start.bat。"""

import io, sys

H = r"E:\dshwork\Demon\src\ui\MainWindow.h"
C = r"E:\dshwork\Demon\src\ui\MainWindow.cpp"

h = io.open(H, encoding="utf-8").read()
for line in ("    QTimer* m_openTimer = nullptr;\n", "    int m_openTries = 0;\n", "    int m_browserCountBefore = -1;\n"):
    if line in h:
        h = h.replace(line, "")
        print("[OK] 移除头文件成员:", line.strip())
io.open(H, "w", encoding="utf-8", newline="").write(h)

c = io.open(C, encoding="utf-8").read()

# 1) 删除构造里的 m_openTimer 整块
start = c.find("    // 启动酒馆后：轮询端口，就绪即自动打开浏览器")
end = c.find("    });", start)
if start >= 0 and end > start:
    end += len("    });\n")
    c = c[:start] + c[end:]
    print("[OK] 删除 openTimer 构造块")
else:
    print("[warn] openTimer 构造块未命中")

# 2) 启动按钮：只拉 Start.bat，不再自己开浏览器
old = '''        if (AppController::portOpen(static_cast<quint16>(m_stPort->value()))) {
            // 已经在跑：直接打开页面
            m_controller->openInEdge(QStringLiteral("http://127.0.0.1:%1/").arg(m_stPort->value()));
            Log::info(QStringLiteral("酒馆已在运行，直接用 Edge 打开页面"));
        } else {
            m_openTries = 0;
            m_openTimer->start();
            Log::info(QStringLiteral("已启动酒馆，等待端口就绪后自动打开浏览器"));
        }'''
new = '''        if (AppController::portOpen(static_cast<quint16>(m_stPort->value()))) {
            // 已经在跑：Start.bat 不会再开浏览器，这里给个手动入口
            m_controller->openInEdge(QStringLiteral("http://127.0.0.1:%1/").arg(m_stPort->value()));
            Log::info(QStringLiteral("酒馆已在运行，打开页面"));
        } else {
            // 未运行：只拉起 Start.bat，浏览器由它自己打开
            Log::info(QStringLiteral("已启动酒馆（浏览器由 Start.bat 打开）"));
        }'''
if old in c:
    c = c.replace(old, new, 1)
    print("[OK] 启动按钮逻辑")
else:
    print("[warn] 启动按钮锚点未命中")

io.open(C, "w", encoding="utf-8", newline="").write(c)
print("done")
