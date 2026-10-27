# -*- coding: utf-8 -*-
import io

S = r"E:\dshwork\dsh-demon\services\dsh-demon\src\server.js"
D = r"E:\dshwork\dsh-demon\services\dsh-demon\src\db.js"

d = io.open(D, encoding="utf-8").read()
if "CREATE TABLE IF NOT EXISTS meta" not in d:
    d = d.replace("CREATE TABLE IF NOT EXISTS chat_files", "CREATE TABLE IF NOT EXISTS meta (\n  key TEXT PRIMARY KEY,\n  value TEXT\n);\n\nCREATE TABLE IF NOT EXISTS chat_files", 1)
    d = d.replace("export function upsertEmotion", """export function getMeta(key, fallback = '') {
  const row = db.prepare('SELECT value FROM meta WHERE key = ?').get(key);
  return row ? row.value : fallback;
}

export function setMeta(key, value) {
  db.prepare('INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value')
    .run(key, String(value));
}

export function upsertEmotion""", 1)
    io.open(D, "w", encoding="utf-8", newline="").write(d)

s = io.open(S, encoding="utf-8").read()
if "/v1/config" not in s:
    s = s.replace("import { appendMemory, getEmotion, queryMemory, upsertEmotion } from './db.js';",
                  "import { appendMemory, getEmotion, getMeta, queryMemory, setMeta, upsertEmotion } from './db.js';")
    s = s.replace("app.get('/v1/stats'", """app.get('/v1/config', async () => ({
  ok: true,
  autoTransfer: getMeta('autoTransfer', '1') === '1',
}));

app.post('/v1/config', async (request) => {
  const body = request.body || {};
  if (typeof body.autoTransfer === 'boolean') {
    setMeta('autoTransfer', body.autoTransfer ? '1' : '0');
    log(`[config] autoTransfer=${body.autoTransfer}`);
  }
  return { ok: true, autoTransfer: getMeta('autoTransfer', '1') === '1' };
});

app.get('/v1/stats'""", 1)

    s = s.replace("""await scanAll(true);
setInterval(() => scanAll(false), config.chatScanMs);
setInterval(() => {
  try {
    scanWorlds({ verbose: false });
  } catch (error) {
    log('[worlds] failed:', error.message);
  }
}, config.worldScanMs);""",
"""function autoTransferEnabled() {
  return getMeta('autoTransfer', '1') === '1';
}

if (autoTransferEnabled()) {
  await scanAll(true);
} else {
  log('[scan] autoTransfer=off，跳过启动扫描');
}
setInterval(() => {
  if (autoTransferEnabled()) scanAll(false);
}, config.chatScanMs);
setInterval(() => {
  if (!autoTransferEnabled()) return;
  try {
    scanWorlds({ verbose: false });
  } catch (error) {
    log('[worlds] failed:', error.message);
  }
}, config.worldScanMs);""", 1)
    io.open(S, "w", encoding="utf-8", newline="").write(s)
print("autoTransfer added")
