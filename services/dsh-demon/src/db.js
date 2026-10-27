import fs from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { config } from './config.js';

fs.mkdirSync(config.dataDir, { recursive: true });
export const db = new DatabaseSync(config.dbPath);

db.exec(`
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS chat_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT UNIQUE NOT NULL,
  character TEXT,
  size INTEGER DEFAULT 0,
  mtime INTEGER DEFAULT 0,
  line_count INTEGER DEFAULT 0,
  status TEXT DEFAULT 'active',
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_file_id INTEGER NOT NULL REFERENCES chat_files(id) ON DELETE CASCADE,
  line_no INTEGER NOT NULL,
  role TEXT NOT NULL,
  text TEXT NOT NULL,
  text_hash TEXT NOT NULL,
  sent_at TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(chat_file_id, line_no)
);

CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  character TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'episodic',
  text TEXT NOT NULL,
  source TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS emotion_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  character TEXT,
  subject TEXT NOT NULL,
  label TEXT NOT NULL,
  intensity REAL,
  source TEXT,
  at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS emotion_state (
  character TEXT NOT NULL,
  subject TEXT NOT NULL,
  label TEXT NOT NULL,
  intensity REAL,
  source TEXT,
  revision INTEGER DEFAULT 1,
  updated_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (character, subject)
);

CREATE TABLE IF NOT EXISTS world_sources (
  kind TEXT NOT NULL,
  path TEXT NOT NULL,
  hash TEXT,
  synced_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (kind, path)
);
`);

export function getMeta(key, fallback = '') {
  const row = db.prepare('SELECT value FROM meta WHERE key = ?').get(key);
  return row ? row.value : fallback;
}

export function setMeta(key, value) {
  db.prepare('INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value')
    .run(key, String(value));
}

export function upsertEmotion({ character = 'default', subject, label, intensity = null, source = 'audio' }) {
  db.prepare(`
    INSERT INTO emotion_state (character, subject, label, intensity, source, revision, updated_at)
    VALUES (?, ?, ?, ?, ?, 1, datetime('now'))
    ON CONFLICT(character, subject) DO UPDATE SET
      label = excluded.label,
      intensity = excluded.intensity,
      source = excluded.source,
      revision = emotion_state.revision + 1,
      updated_at = datetime('now')
  `).run(character, subject, label, intensity, source);
  db.prepare(`
    INSERT INTO emotion_events (character, subject, label, intensity, source, at)
    VALUES (?, ?, ?, ?, ?, datetime('now'))
  `).run(character, subject, label, intensity, source);
}

export function getEmotion(character = 'default') {
  const rows = db.prepare('SELECT subject, label, intensity, source, revision, updated_at FROM emotion_state WHERE character = ?').all(character);
  const out = { character, revision: 0 };
  for (const row of rows) {
    out[row.subject] = {
      label: row.label,
      intensity: row.intensity,
      source: row.source,
      at: row.updated_at,
      revision: row.revision,
    };
    out.revision = Math.max(out.revision, row.revision);
  }
  return out;
}

export function appendMemory({ character, kind = 'episodic', text, source = '' }) {
  db.prepare('INSERT INTO memories (character, kind, text, source) VALUES (?, ?, ?, ?)')
    .run(character, kind, text, source);
  return db.prepare('SELECT last_insert_rowid() AS id').get().id;
}

export function queryMemory({ character, query, limit = 8 }) {
  const like = `%${query}%`;
  const rows = db.prepare(`
    SELECT id, character, kind, text, created_at
    FROM memories
    WHERE character = ? AND text LIKE ?
    ORDER BY id DESC LIMIT ?
  `).all(character, like, limit);
  return rows.map((row) => ({ ...row, score: 1 }));
}
