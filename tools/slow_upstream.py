# -*- coding: utf-8 -*-
"""慢上游：故意沉默 6 秒再吐字，用来验证 Demon 的 SSE 保活。"""

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8897


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        print("[slow] 沉默 6 秒…", flush=True)
        time.sleep(6)

        for tok in ["慢", "上", "游", "到", "了"]:
            chunk = {
                "id": "chatcmpl-slow",
                "object": "chat.completion.chunk",
                "model": "slow-model",
                "choices": [{"index": 0, "delta": {"content": tok}, "finish_reason": None}],
            }
            self.wfile.write(("data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n").encode())
            self.wfile.flush()
            time.sleep(0.2)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        print("[slow] 完成", flush=True)


if __name__ == "__main__":
    print(f"slow upstream on {PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
