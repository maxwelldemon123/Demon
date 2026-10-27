import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const dataDir = process.env.DSH_DEMON_DATA
  || path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), '.local', 'share'), 'dsh-demon');

const stDataDir = process.env.DSH_DEMON_ST_DATA
  || 'C:/mylove/SillyTavern/data/default-user';

export const config = {
  host: '127.0.0.1',
  port: Number(process.env.DSH_DEMON_PORT || 8791),
  dataDir,
  dbPath: path.join(dataDir, 'memory.sqlite'),
  tokenPath: path.join(dataDir, 'token'),
  stDataDir,
  chatsDir: path.join(stDataDir, 'chats'),
  worldsDir: path.join(stDataDir, 'worlds'),
  charactersDir: path.join(stDataDir, 'characters'),
  chatScanMs: Number(process.env.DSH_DEMON_SCAN_MS || 86_400_000),
  worldScanMs: Number(process.env.DSH_DEMON_WORLD_SCAN_MS || 604_800_000),
  version: '0.1.0',
  contract: '1.0.0',
};

export function ensureDataDir() {
  fs.mkdirSync(config.dataDir, { recursive: true });
}

export function loadOrCreateToken() {
  ensureDataDir();
  if (fs.existsSync(config.tokenPath)) {
    return fs.readFileSync(config.tokenPath, 'utf8').trim();
  }
  const token = [...crypto.getRandomValues(new Uint8Array(24))]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  fs.writeFileSync(config.tokenPath, token, { mode: 0o600 });
  return token;
}
