# -*- coding: utf-8 -*-
"""加前置声明（spawnCommandLine / defaultBrowserExe 定义在文件后面）。"""

import io

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()

decl = """namespace {
bool spawnCommandLine(const QString& commandLine);
QString defaultBrowserExe();
} // namespace

"""

if "bool spawnCommandLine(const QString& commandLine);" not in t:
    anchor = "namespace {\n\nQByteArray jsonErrorBody"
    if anchor not in t:
        # 退而求其次：插在第一个 namespace { 之前
        idx = t.find("namespace {")
    else:
        idx = t.find(anchor)
    if idx < 0:
        print("[MISS] namespace")
        raise SystemExit(1)
    t = t[:idx] + decl + t[idx:]
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("[OK] 前置声明")
else:
    print("[skip] 已有声明")
