// Shared boot: loads published data + opens the persisted store + builds the
// service. Imported by both index.mjs (HTTP server) and cli.mjs (admin tools)
// so there is exactly one place that knows how data is loaded and persisted.
import { randomUUID, randomBytes, webcrypto } from 'node:crypto';
import { readFile, writeFile, mkdir, rename } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { createService } from '../js/core/service.js';
import { createStore } from '../js/core/store.js';
import { validateConfig } from '../js/core/config.js';

const { subtle } = webcrypto;
const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = path.resolve(__dirname, '..');
export const DATA_DIR = process.env.DATA_DIR || '/opt/shifokor_data';

async function loadJson(relPath) {
  return JSON.parse(await readFile(path.join(PROJECT_ROOT, relPath), 'utf8'));
}

export const [config, plans, rules, specialties, thresholds, sources, parametersRaw, formulaIndex] = await Promise.all([
  loadJson('config/app.json'), loadJson('data/plans.json'), loadJson('data/rules.json'),
  loadJson('data/specialties.json'), loadJson('data/thresholds.json'), loadJson('data/sources.json'),
  loadJson('data/parameters.json'), loadJson('data/formulas/index.json'),
]);
export const formulas = await Promise.all(formulaIndex.calculators.map((id) => loadJson(`data/formulas/${id}.json`)));
export const dicts = Object.fromEntries(await Promise.all(
  config.supportedLanguages.map(async (l) => [l, await loadJson(`data/i18n/${l}.json`)]),
));
const cfgErrors = validateConfig(config);
if (cfgErrors.length) {
  console.error('config/app.json invalid:', cfgErrors);
  process.exit(1);
}

await mkdir(DATA_DIR, { recursive: true });
async function readJsonFile(file, fallback) {
  try { return JSON.parse(await readFile(path.join(DATA_DIR, file), 'utf8')); } catch { return fallback; }
}
async function writeJsonFileAtomic(file, value) {
  const dest = path.join(DATA_DIR, file);
  const tmp = `${dest}.tmp-${process.pid}`;
  await writeFile(tmp, JSON.stringify(value));
  await rename(tmp, dest);
}

let dbSaving = Promise.resolve();
export const store = createStore(await readJsonFile('db.json', {}), (snapshot) => {
  dbSaving = dbSaving.then(() => writeJsonFileAtomic('db.json', snapshot)).catch((e) => console.error('db persist failed', e));
});

// Callers that need to exit right after a write (cli.mjs) must await this.
export function waitForPersist() {
  return dbSaving;
}

const ITERATIONS = 100000;
const b64 = (buf) => Buffer.from(buf).toString('base64');
const unb64 = (s) => new Uint8Array(Buffer.from(s, 'base64'));
async function pbkdf2(password, salt, iterations) {
  const key = await subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
  return subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt, iterations }, key, 256);
}
export const hasher = {
  async hash(password) {
    const salt = randomBytes(16);
    return `pbkdf2$${ITERATIONS}$${b64(salt)}$${b64(await pbkdf2(password, salt, ITERATIONS))}`;
  },
  async verify(password, stored) {
    const [scheme, iter, salt, hash] = String(stored).split('$');
    if (scheme !== 'pbkdf2') return false;
    return b64(await pbkdf2(password, unb64(salt), Number(iter))) === hash;
  },
};

export const service = createService({ store, hasher, randomId: randomUUID, config, plans, rules, specialties, thresholds });

// Sessions are infra, not business data — kept separate from db.json.
let sessionsSaving = Promise.resolve();
export const sessions = await readJsonFile('sessions.json', {});
export function persistSessions() {
  sessionsSaving = sessionsSaving.then(() => writeJsonFileAtomic('sessions.json', sessions))
    .catch((e) => console.error('session persist failed', e));
  return sessionsSaving;
}
