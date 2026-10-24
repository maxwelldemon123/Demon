# -*- coding: utf-8 -*-
import io

p = r"E:\dshwork\Demon\tools\smoke_test.py"
t = io.open(p, encoding="utf-8").read()
t = t.replace('payload = {"model": "demon", "stream": True,', 'payload = {"model": "fake-model", "stream": True,')
t = t.replace('for model in ("fake-model", "demon", "不存在"):', 'for model in ("fake-model", "local-vl", "不存在"):')
io.open(p, "w", encoding="utf-8", newline="").write(t)
print("smoke test updated")
