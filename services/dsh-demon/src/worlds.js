import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { db } from './db.js';
import { config } from './config.js';

function listFiles(dir, suffix) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(suffix))
    .map((entry) => path.join(dir, entry.name));
}

function fileHash(file) {
  const stat = fs.statSync(file);
  return crypto.createHash('sha1')
    .update(`${stat.size}:${stat.mtimeMs}:${path.basename(file)}`)
    .digest('hex');
}

export function scanWorlds({ verbose = false } = {}) {
  const items = [
    ...listFiles(config.worldsDir, '.json').map((file) => ['world', file]),
    ...listFiles(config.charactersDir, '.png').map((file) => ['character', file]),
  ];
  const stmt = db.prepare(`
    INSERT INTO world_sources (kind, path, hash, synced_at)
    VALUES (?, ?, ?, datetime('now'))
    ON CONFLICT(kind, path) DO UPDATE SET hash = excluded.hash, synced_at = datetime('now')
  `);
  for (const [kind, file] of items) {
    try {
      stmt.run(kind, file, fileHash(file));
    } catch {
      // 文件正在被写时跳过，下次扫描再来
    }
  }
  if (verbose) {
    console.log(`[worlds] ${items.length} files`);
  }
  return { files: items.length };
}
