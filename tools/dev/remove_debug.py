# -*- coding: utf-8 -*-
"""移除诊断接口。"""

import io, sys

P = r"E:\dshwork\Demon\src\app\AppController.cpp"
t = io.open(P, encoding="utf-8").read()

start = t.find('    if (request.path == QStringLiteral("/debug/child")) {')
end = t.find('    if (request.path == QStringLiteral("/launcher/open")) {', start)
if start >= 0 and end > start:
    t = t[:start] + t[end:]
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("[OK] 删除 /debug/child")
else:
    print("[skip] 未找到")
