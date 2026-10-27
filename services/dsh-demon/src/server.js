import Fastify from 'fastify';
import websocket from '@fastify/websocket';
import { config, loadOrCreateToken } from './config.js';
import { appendMemory, getEmotion, getMeta, queryMemory, setMeta, upsertEmotion } from './db.js';
import { chatStats, scanChats } from './chats.js';
import { scanWorlds } from './worlds.js';

const token = loadOrCreateToken();
const app = Fastify({ logger: false });

await app.register(websocket);

const clients = new Set();

function broadcast(payload) {
  const text = JSON.stringify(payload);
  for (const socket of clients) {
    try {
      socket.send(text);
    } catch {
      clients.delete(socket);
    }
  }
}

function log(...args) {
  console.log(new Date().toISOString(), ...args);
}

app.addHook('onRequest', async (request, reply) => {
  if (request.url.startsWith('/v1/health')) return;
  const provided = request.headers['x-dsh-token'] || request.query?.token;
  if (provided !== token) {
    reply.code(401).send({ ok: false, error: 'unauthorized' });
  }
});

app.get('/v1/health', async () => ({
  ok: true,
  service: 'dsh-demon',
  version: config.version,
  contract: config.contract,
  uptime: process.uptime(),
}));

app.get('/v1/config', async () => ({
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

app.get('/v1/stats', async () => ({
  ok: true,
  chats: chatStats(),
  emotion: getEmotion(),
}));

app.post('/v1/memory/append', async (request) => {
  const body = request.body || {};
  if (!body.character || !body.text) {
    return { ok: false, error: 'character and text required' };
  }
  const id = appendMemory({
    character: body.character,
    kind: body.kind || 'episodic',
    text: body.text,
    source: body.source || '',
  });
  return { ok: true, id };
});

app.post('/v1/memory/query', async (request) => {
  const body = request.body || {};
  if (!body.character || !body.query) {
    return { ok: false, error: 'character and query required', items: [] };
  }
  const items = queryMemory({
    character: body.character,
    query: body.query,
    limit: Math.min(Number(body.limit) || 8, 50),
  });
  return { ok: true, items };
});

app.get('/v1/state/emotion', async (request) => ({
  ok: true,
  ...getEmotion(request.query?.character || 'default'),
}));

app.post('/v1/state/emotion', async (request) => {
  const body = request.body || {};
  if (!body.subject || !body.label) {
    return { ok: false, error: 'subject and label required' };
  }
  upsertEmotion({
    character: body.character || 'default',
    subject: body.subject,
    label: body.label,
    intensity: body.intensity ?? null,
    source: body.source || 'manual',
  });
  const state = getEmotion(body.character || 'default');
  broadcast({ type: 'emotion_state', ...state });
  return { ok: true, state };
});

app.post('/v1/events', async (request) => {
  const event = request.body || {};
  if (event.type === 'emotion') {
    upsertEmotion({
      character: event.character || 'default',
      subject: event.subject || 'user',
      label: event.emotion,
      intensity: event.intensity ?? null,
      source: event.source || 'audio',
    });
  }
  broadcast(event);
  return { ok: true };
});

app.get('/v1/events', { websocket: true }, (socket, request) => {
  const provided = request.query?.token;
  if (provided !== token) {
    socket.close(1008, 'unauthorized');
    return;
  }
  clients.add(socket);
  socket.send(JSON.stringify({ type: 'hello', service: 'dsh-demon', version: config.version }));
  socket.on('message', (raw) => {
    try {
      const event = JSON.parse(raw.toString());
      broadcast(event);
    } catch {
      // 忽略非法消息
    }
  });
  socket.on('close', () => clients.delete(socket));
});

app.post('/v1/sync', async (request) => {
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

app.get('/v1/chat/messages', async (request) => {
  const { character, limit = 50 } = request.query || {};
  const { db } = await import('./db.js');
  const rows = db.prepare(`
    SELECT m.id, m.role, m.text, m.sent_at, c.character
    FROM messages m JOIN chat_files c ON c.id = m.chat_file_id
    WHERE (? IS NULL OR c.character = ?)
    ORDER BY m.id DESC LIMIT ?
  `).all(character || null, character || null, Math.min(Number(limit) || 50, 200));
  return { ok: true, items: rows.reverse() };
});

async function scanAll(verbose = false) {
  try {
    const chats = scanChats({ verbose });
    const worlds = scanWorlds({ verbose });
    if (verbose) log(`[scan] chats=${chats.files} new=${chats.newMessages} worlds=${worlds.files}`);
  } catch (error) {
    log('[scan] failed:', error.message);
  }
}

function autoTransferEnabled() {
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
}, config.worldScanMs);

await app.listen({ host: config.host, port: config.port });
log(`dsh-demon ${config.version} listening on http://${config.host}:${config.port}`);
log(`token: ${config.tokenPath}`);
