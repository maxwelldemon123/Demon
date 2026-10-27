import { scanChats, chatStats } from './chats.js';
import { scanWorlds } from './worlds.js';

const chats = scanChats({ verbose: true });
const worlds = scanWorlds({ verbose: true });
console.log(JSON.stringify({ ok: true, chats, worlds, stats: chatStats() }, null, 2));
