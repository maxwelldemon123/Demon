# -*- coding: utf-8 -*-
import io

P = r"E:\dshwork\dsh-demon\services\dsh-demon\src\config.js"
t = io.open(P, encoding="utf-8").read()
t = t.replace("chatScanMs: Number(process.env.DSH_DEMON_SCAN_MS || 60_000),",
              "chatScanMs: Number(process.env.DSH_DEMON_SCAN_MS || 86_400_000),")
t = t.replace("worldScanMs: 300_000,", "worldScanMs: Number(process.env.DSH_DEMON_WORLD_SCAN_MS || 604_800_000),")
io.open(P, "w", encoding="utf-8", newline="").write(t)

S = r"E:\dshwork\dsh-demon\services\dsh-demon\src\server.js"
s = io.open(S, encoding="utf-8").read()
if "/v1/sync" not in s:
    s = s.replace("app.get('/v1/chat/messages'", """app.post('/v1/sync', async (request) => {
  const body = request.body || {};
  const wantChats = body.chats !== false;
  const wantWorlds = body.worlds !== false;
  const result = { ok: true, chats: null, worlds: null };
  if (wantChats) {
    result.chats = scanChats({ verbose: true });
  }
  if (wantWorlds) {
    result.worlds = scanWorlds({ verbose: true });
  }
  broadcast({ type: 'sync_done', at: new Date().toISOString(), ...result });
  return result;
});

app.get('/v1/chat/messages'""")
    io.open(S, "w", encoding="utf-8", newline="").write(s)
print("service patched")
