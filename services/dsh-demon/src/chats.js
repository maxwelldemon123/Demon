import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { db } from './db.js';
import { config } from './config.js';

function walk(dir, suffix, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, suffix, out);
    else if (entry.name.endsWith(suffix)) out.push(full);
  }
  return out;
}

function hash(text) {
  return crypto.createHash('sha1').update(text).digest('hex');
}

function characterOf(file) {
  const rel = path.relative(config.chatsDir, file);
  const parts = rel.split(path.sep);
  return parts.length > 1 ? parts[0] : 'default';
}

export function scanChats({ verbose = false } = {}) {
  const stats = { files: 0, newMessages: 0, reset: 0 };
  const files = walk(config.chatsDir, '.jsonl');
  for (const file of files) {
    let stat;
    try {
      stat = fs.statSync(file);
    } catch {
      continue;
    }
    const character = characterOf(file);
    let row = db.prepare('SELECT id, size, line_count FROM chat_files WHERE path = ?').get(file);
    if (!row) {
      db.prepare('INSERT INTO chat_files (path, character, size, mtime, line_count) VALUES (?, ?, ?, ?, 0)')
        .run(file, character, stat.size, Math.floor(stat.mtimeMs));
      row = db.prepare('SELECT id, size, line_count FROM chat_files WHERE path = ?').get(file);
    }

    const raw = fs.readFileSync(file, 'utf8');
    const lines = raw.split(/\r?\n/).filter((line) => line.trim().length > 0);

    let startLine = row.line_count;
    if (stat.size < row.size || startLine > lines.length) {
      db.prepare('DELETE FROM messages WHERE chat_file_id = ?').run(row.id);
      startLine = 0;
      stats.reset++;
    }

    for (let i = startLine; i < lines.length; i++) {
      if (i === 0) continue; // 首行是 chat_metadata
      let obj;
      try {
        obj = JSON.parse(lines[i]);
      } catch {
        continue;
      }
      const text = typeof obj.mes === 'string' ? obj.mes.trim() : '';
      if (!text) continue;
      const role = obj.is_user ? 'user' : 'assistant';
      const result = db.prepare(`
        INSERT OR IGNORE INTO messages (chat_file_id, line_no, role, text, text_hash, sent_at)
        VALUES (?, ?, ?, ?, ?, ?)
      `).run(row.id, i, role, text, hash(text), obj.send_date || null);
      if (result.changes > 0) stats.newMessages++;
    }

    db.prepare('UPDATE chat_files SET size = ?, mtime = ?, line_count = ?, character = ?, status = ?, updated_at = datetime(\'now\') WHERE id = ?')
      .run(stat.size, Math.floor(stat.mtimeMs), lines.length, character, 'active', row.id);
    stats.files++;
  }

  if (verbose) {
    console.log(`[chats] files=${stats.files} new=${stats.newMessages} reset=${stats.reset}`);
  }
  return stats;
}

export function chatStats() {
  const files = db.prepare('SELECT COUNT(*) AS n FROM chat_files').get().n;
  const messages = db.prepare('SELECT COUNT(*) AS n FROM messages').get().n;
  const memories = db.prepare('SELECT COUNT(*) AS n FROM memories').get().n;
  return { files, messages, memories };
}
