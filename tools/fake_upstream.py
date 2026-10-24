# -*- coding: utf-8 -*-
"""假上游：模拟 OpenAI 兼容的 SSE 流式接口，用于本地验证 Demon 的透传。"""

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import sys
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
TAG = sys.argv[2] if len(sys.argv) > 2 else "A"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 安静一点
        print("[fake-upstream]", fmt % args, flush=True)

    def do_GET(self):
        body = json.dumps({"object": "list", "data": [{"id": "fake-model", "object": "model"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}

        model = payload.get("model", "?")
        messages = payload.get("messages", [])
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = str(m.get("content", ""))[:40]
                break

        print(f"[fake-upstream] model={model} user={last_user!r} stream={payload.get('stream')}", flush=True)

        if not payload.get("stream"):
            body = json.dumps(
                {
                    "id": "chatcmpl-fake",
                    "object": "chat.completion",
                    "model": model,
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "（非流式）你好。"}, "finish_reason": "stop"}],
                },
                ensure_ascii=False,
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        tokens = [f"[{TAG}]", "器", "在", "线", "。", "来", "自", "上", "游", TAG, "。"] if TAG != "A" else ["你", "好", "，", "我", "是", "Demon", "。"]
        for i, tok in enumerate(tokens):
            chunk = {
                "id": "chatcmpl-fake",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{"index": 0, "delta": {"content": tok}, "finish_reason": None}],
            }
            data = "data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n"
            self.wfile.write(data.encode("utf-8"))
            self.wfile.flush()
            time.sleep(0.12)

        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"fake upstream on http://127.0.0.1:{PORT}/v1", flush=True)
    server.serve_forever()
