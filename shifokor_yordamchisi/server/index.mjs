// Node server for "Шифокор ёрдамчиси". Zero npm dependencies — built-ins only,
// matching the rest of this project (no build step, hand-rolled everything).
// Business logic lives in ../js/core/service.js and is imported unchanged via
// context.mjs — this file is transport only: HTTP routing, sessions, AI call.
import { createServer } from 'node:http';
import { randomBytes } from 'node:crypto';

import { ServiceError } from '../js/core/service.js';
import { resolveParameters } from '../js/core/thresholds.js';
import { buildKnowledge, buildSystemPrompt, checkAnswer, detectInjection, validateChat } from '../js/core/ai-guard.js';
import {
  service, sources, parametersRaw, formulas, rules, dicts, thresholds, sessions, persistSessions,
} from './context.mjs';

const PORT = Number(process.env.PORT || 8020);
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || '';
const ANTHROPIC_MODEL = process.env.ANTHROPIC_MODEL || 'claude-opus-4-8';
const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;
const MAX_BODY = 256 * 1024;

// ---- sessions (sid -> {userId, expiresAt}) ---------------------------------
function createSession(userId) {
  const sid = randomBytes(32).toString('hex');
  sessions[sid] = { userId, expiresAt: Date.now() + SESSION_TTL_MS };
  persistSessions();
  return sid;
}
function sessionUser(sid) {
  const s = sid && sessions[sid];
  if (!s) return null;
  if (s.expiresAt < Date.now()) { delete sessions[sid]; persistSessions(); return null; }
  return service.getUser(s.userId);
}
function destroySession(sid) {
  if (sid && sessions[sid]) { delete sessions[sid]; persistSessions(); }
}

// ---- AI call (real Anthropic Messages API; same guardrails as the demo backend) --
async function callAnthropic(system, messages) {
  if (!ANTHROPIC_API_KEY) throw new Error('ANTHROPIC_API_KEY not set');
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-api-key': ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({
      model: ANTHROPIC_MODEL, max_tokens: 1024, system,
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
    }),
  });
  if (!res.ok) throw new Error(`anthropic_${res.status}: ${(await res.text().catch(() => '')).slice(0, 300)}`);
  const data = await res.json();
  return (data.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
}

async function handleAiChat(actor, body) {
  if (!actor) throw new ServiceError('notSignedIn', 401);
  const eff = service.effective();
  if (!eff.config.aiEnabled) throw new ServiceError('aiDisabled', 400);
  const messages = Array.isArray(body.messages) ? body.messages : [];
  const invalid = validateChat(messages);
  if (invalid) throw new ServiceError(invalid, 400);
  const quota = service.aiQuota(actor);
  if (quota.remaining <= 0) throw new ServiceError('quotaExceeded', 429);
  if (detectInjection(messages[messages.length - 1].content)) {
    service.recordUsage(actor, { outcome: 'blocked_injection' });
    throw new ServiceError('injection', 400);
  }
  const knowledge = buildKnowledge({
    sources, parameters: resolveParameters(parametersRaw, eff.thresholds), formulas, rules,
    dict: dicts.en, thresholds, thresholdValues: eff.thresholds,
  });
  const system = buildSystemPrompt(knowledge, body.lang);
  let text;
  try {
    text = await callAnthropic(system, messages);
  } catch (e) {
    console.error('anthropic call failed:', e.message);
    throw new ServiceError('aiUnavailable', 502);
  }
  const checked = checkAnswer(text, sources.sources.map((s) => s.id));
  service.recordUsage(actor, { outcome: checked.ok ? 'ok' : 'no_source' });
  if (!checked.ok) throw new ServiceError('noSource', 422);
  return { text: checked.text, sourceIds: checked.sourceIds };
}

// ---- tiny HTTP plumbing (no framework) -------------------------------------
function parseCookies(header) {
  const out = {};
  (header || '').split(';').forEach((p) => {
    const i = p.indexOf('=');
    if (i > -1) out[p.slice(0, i).trim()] = decodeURIComponent(p.slice(i + 1).trim());
  });
  return out;
}
function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > MAX_BODY) { reject(new Error('bodyTooLarge')); req.destroy(); return; }
      chunks.push(c);
    });
    req.on('end', () => {
      if (!chunks.length) return resolve({});
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); } catch { reject(new Error('badJson')); }
    });
    req.on('error', reject);
  });
}
function send(res, status, body) {
  const json = JSON.stringify(body ?? {});
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'content-length': Buffer.byteLength(json) });
  res.end(json);
}
function fail(res, err) {
  if (err instanceof ServiceError) return send(res, err.status, { error: err.code, details: err.details });
  console.error(err);
  send(res, 500, { error: 'serverError' });
}
function match(pattern, pathname) {
  const pParts = pattern.split('/').filter(Boolean);
  const uParts = pathname.split('/').filter(Boolean);
  if (pParts.length !== uParts.length) return null;
  const params = {};
  for (let i = 0; i < pParts.length; i++) {
    if (pParts[i].startsWith(':')) params[pParts[i].slice(1)] = decodeURIComponent(uParts[i]);
    else if (pParts[i] !== uParts[i]) return null;
  }
  return params;
}
function setSessionCookie(req, res, sid) {
  const secure = req.headers['x-forwarded-proto'] === 'https' ? '; Secure' : '';
  res.setHeader('Set-Cookie', `sid=${sid}; HttpOnly${secure}; SameSite=Lax; Path=/; Max-Age=${Math.floor(SESSION_TTL_MS / 1000)}`);
}
function clearSessionCookie(req, res) {
  const secure = req.headers['x-forwarded-proto'] === 'https' ? '; Secure' : '';
  res.setHeader('Set-Cookie', `sid=; HttpOnly${secure}; SameSite=Lax; Path=/; Max-Age=0`);
}
function clientIp(req) {
  const xf = req.headers['x-forwarded-for'];
  return xf ? xf.split(',')[0].trim() : req.socket.remoteAddress;
}

// crude per-IP throttle on auth endpoints (login/register) — not a substitute
// for a real WAF, but cheap insurance against naive brute-forcing.
const attempts = new Map();
function tooManyAttempts(bucket, ip) {
  const key = `${bucket}:${ip}`;
  const now = Date.now();
  const arr = (attempts.get(key) || []).filter((t) => now - t < 5 * 60 * 1000);
  arr.push(now);
  attempts.set(key, arr);
  return arr.length > 10;
}

const server = createServer(async (req, res) => {
  const started = Date.now();
  res.on('finish', () => console.log(`${req.method} ${req.url} ${res.statusCode} ${Date.now() - started}ms`));
  try {
    const url = new URL(req.url, 'http://internal');
    const pathname = url.pathname;
    if (!pathname.startsWith('/api/')) return send(res, 404, { error: 'notFound' });
    const sub = pathname.slice(4);
    const cookies = parseCookies(req.headers.cookie);
    const actor = sessionUser(cookies.sid);

    if (req.method === 'GET' && sub === '/health') return send(res, 200, { ok: true });

    let body = {};
    if (req.method === 'POST') {
      try { body = (await readBody(req)) || {}; }
      catch (e) { return send(res, e.message === 'bodyTooLarge' ? 413 : 400, { error: 'badRequest' }); }
    }

    if (req.method === 'GET' && sub === '/me') return send(res, 200, { user: service.me(actor) });

    if (req.method === 'POST' && sub === '/auth/register') {
      if (tooManyAttempts('register', clientIp(req))) return send(res, 429, { error: 'tooManyAttempts' });
      const user = await service.register(body);
      const sid = createSession(user.id);
      setSessionCookie(req, res, sid);
      return send(res, 200, { user: service.me(service.getUser(user.id)) });
    }
    if (req.method === 'POST' && sub === '/auth/login') {
      if (tooManyAttempts('login', clientIp(req))) return send(res, 429, { error: 'tooManyAttempts' });
      const user = await service.login(body.email, body.password);
      const sid = createSession(user.id);
      setSessionCookie(req, res, sid);
      return send(res, 200, { user: service.me(service.getUser(user.id)) });
    }
    if (req.method === 'POST' && sub === '/auth/logout') {
      destroySession(cookies.sid);
      clearSessionCookie(req, res);
      return send(res, 200, {});
    }
    if (req.method === 'GET' && sub === '/admin/users') return send(res, 200, { users: service.listUsers(actor) });
    {
      const p = match('/admin/users/:id/verify', sub);
      if (p && req.method === 'POST') return send(res, 200, { user: await service.verifyDoctor(actor, p.id, body.action, body.note) });
    }
    if (req.method === 'GET' && sub === '/admin/journal') return send(res, 200, { entries: service.journal(actor, url.searchParams.get('kind') || undefined) });
    if (req.method === 'GET' && sub === '/admin/rule-decisions') return send(res, 200, { decisions: service.ruleDecisions(actor) });
    if (req.method === 'GET' && sub === '/rules/status') return send(res, 200, { statuses: service.ruleStatuses() });
    {
      const p = match('/rules/:id/decision', sub);
      if (p && req.method === 'POST') return send(res, 200, await service.decideRule(actor, p.id, body.action));
    }
    if (req.method === 'POST' && sub === '/conclusions/approve') return send(res, 200, await service.approveConclusion(actor, body.ruleIds));
    if (req.method === 'POST' && sub === '/questions') return send(res, 200, await service.createQuestion(actor, body));
    if (req.method === 'GET' && sub === '/questions') return send(res, 200, await service.listQuestions(actor));
    {
      const p = match('/questions/:id/answer', sub);
      if (p && req.method === 'POST') return send(res, 200, await service.answerQuestion(actor, p.id, body.text));
    }
    if (req.method === 'GET' && sub === '/plans') return send(res, 200, service.plans());
    if (req.method === 'GET' && sub === '/overrides') return send(res, 200, service.overrides());
    if (req.method === 'POST' && sub === '/admin/overrides') return send(res, 200, await service.setOverride(actor, body.key, body.value));
    if (req.method === 'POST' && sub === '/admin/overrides/reset') return send(res, 200, await service.resetOverride(actor, body.key));
    if (req.method === 'GET' && sub === '/ai/quota') return send(res, 200, service.aiQuota(actor));
    if (req.method === 'POST' && sub === '/billing/cancel') return send(res, 200, await service.cancelSubscription(actor));
    if (req.method === 'POST' && sub === '/billing/checkout') return send(res, 200, await service.startCheckout(actor, { planId: body.planId, providerId: body.providerId }));
    if (req.method === 'POST' && sub === '/ai/chat') return send(res, 200, await handleAiChat(actor, body));

    return send(res, 404, { error: 'notFound' });
  } catch (err) {
    fail(res, err);
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`shifokor-server listening on 127.0.0.1:${PORT}`);
});
