# -*- coding: utf-8 -*-
"""多轮对话稳定性测试：模拟酒馆连续发消息，观察时延/内存/崩溃。"""

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8790"
TURNS = int(sys.argv[1]) if len(sys.argv) > 1 else 4

messages = [{"role": "system", "content": "你是Demon，回答简短，每句不超过20字。"}]
prompts = [
    "你好，报一下名字。",
    "今天天气怎么样？",
    "用一句话说说你现在在做什么。",
    "还记得我第一句问了你什么吗？",
    "最后：说声晚安。",
]

print(f"== 多轮对话（{TURNS} 轮）==")
for i in range(TURNS):
    user = prompts[i % len(prompts)]
    messages.append({"role": "user", "content": user})
    payload = {"model": "demon", "stream": True, "messages": messages}

    t0 = time.time()
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    text = ""
    events = 0
    with urllib.request.urlopen(req, timeout=180) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            payload_str = line[5:].strip()
            if payload_str == "[DONE]":
                continue
            events += 1
            try:
                obj = json.loads(payload_str)
                delta = obj["choices"][0].get("delta", {})
                text += delta.get("content") or ""
            except Exception:
                pass
    dt = time.time() - t0

    print(f"  第 {i+1} 轮: {dt:5.1f}s  事件 {events:3d}  回复[{text.strip()[:40]}]")
    messages.append({"role": "assistant", "content": text})

print("完成，无异常")
