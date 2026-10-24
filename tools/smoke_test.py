# -*- coding: utf-8 -*-
"""Demon 冒烟测试：接口 + 语音 + 流式 + 上游路由。

用法：python tools\smoke_test.py [base_url]
前置：demon.exe 在跑；GPT-SoVITS 在 9880；假上游在 8899。
"""

import json
import sys
import time
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790"
results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  {'✓' if ok else '✗'} {name}" + (f"  [{detail}]" if detail else ""))


def http(method, path, body=None, timeout=180):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def wav_info(data):
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    pos = 12
    rate = 0
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        if cid == b"fmt ":
            rate = int.from_bytes(data[pos + 12:pos + 16], "little")
        elif cid == b"data":
            return {"rate": rate, "seconds": round(size / rate, 2) if rate else 0, "bytes": len(data)}
        pos += 8 + size + (size & 1)
    return None


print("== 1. 基础接口 ==")
st, body, _ = http("GET", "/healthz")
record("GET /healthz", st == 200 and b'"status": "ok"' in body, f"HTTP {st}")

st, body, _ = http("GET", "/v1/models")
record("GET /v1/models", st == 200 and b'"demon"' in body, f"HTTP {st}")

st, body, _ = http("GET", "/voice/status")
voice = json.loads(body)["voice"] if st == 200 else {}
record("GET /voice/status", st == 200 and voice.get("profiles") == ["xiaod", "demon"],
       f"profiles={voice.get('profiles')} autoPlay={voice.get('autoPlay')}")

print("== 2. 语音合成 ==")
t0 = time.time()
st, body, headers = http("POST", "/voice/speak", {"text": "主人，晚上好。", "profile": "xiaod", "lang": "zh"})
info = wav_info(body)
record("xiaod / 中文", st == 200 and info is not None and info["seconds"] > 0.3,
       f"HTTP {st} {info} {round(time.time()-t0,1)}s")

t0 = time.time()
st, body, headers = http("POST", "/voice/speak", {"text": "はい、わかりました。", "profile": "demon", "lang": "ja"})
info = wav_info(body)
record("demon / 日文", st == 200 and info is not None and info["seconds"] > 0.3,
       f"HTTP {st} {info} {round(time.time()-t0,1)}s")

st, body, _ = http("POST", "/voice/speak", {"text": "   "})
record("空文本被拒", st == 400, f"HTTP {st}")

print("== 3. 流式对话（并触发朗读）==")
payload = {"model": "fake-model", "stream": True,
           "messages": [{"role": "user", "content": "测试"}]}
t0 = time.time()
st, body, headers = http("POST", "/v1/chat/completions", payload, timeout=60)
elapsed = time.time() - t0
events = body.count(b"data: ")
has_done = b"data: [DONE]" in body
record("SSE 流式", st == 200 and events >= 5 and has_done,
       f"HTTP {st} events={events} {round(elapsed,2)}s")
record("Content-Type", "text/event-stream" in headers.get("Content-Type", ""), headers.get("Content-Type", ""))

print("== 4. 上游按模型名路由 ==")
for model in ("fake-model", "local-vl", "不存在"):
    st, body, _ = http("POST", "/v1/chat/completions",
                       {"model": model, "stream": True, "messages": [{"role": "user", "content": "hi"}]},
                       timeout=60)
    record(f"model={model}", st == 200 and b"[DONE]" in body, f"HTTP {st}")

print("== 5. 语音队列最终会排空 ==")
time.sleep(1)
deadline = time.time() + 60
drained = False
while time.time() < deadline:
    st, body, _ = http("GET", "/voice/status")
    v = json.loads(body)["voice"]
    if v["queued"] == 0 and not v["busy"]:
        drained = True
        break
    time.sleep(2)
record("队列排空", drained)

print()
passed = sum(1 for _, ok, _ in results if ok)
print(f"通过 {passed}/{len(results)}")
sys.exit(0 if passed == len(results) else 1)
