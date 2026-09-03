import 'dotenv/config';
import express from 'express';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import jwt from 'jsonwebtoken';
import { WebSocketServer } from 'ws';

const PORT = Number(process.env.PORT || 3000);
const USERNAME = process.env.GITHUB_USERNAME || 'Saket745';
const PROFILE_REPO = process.env.GITHUB_PROFILE_REPO || 'Saket745/Saket745';
const APP_ID = process.env.GITHUB_APP_ID;
const INSTALLATION_ID = process.env.GITHUB_INSTALLATION_ID;
const PRIVATE_KEY = process.env.GITHUB_PRIVATE_KEY?.replace(/\\n/g, '\n');
const WEBHOOK_SECRET = process.env.GITHUB_WEBHOOK_SECRET;
const ROOT = path.resolve();
const DATA_DIR = path.join(ROOT, 'data');
const STATE_FILE = path.join(DATA_DIR, 'state.json');

const app = express();
app.use(express.json({
  verify: (req, _res, buf) => { req.rawBody = Buffer.from(buf); },
  limit: '1mb'
}));
app.use(express.static(path.join(ROOT, 'public')));

let state = { generatedAt: null, source: 'github', live: false, profile: {}, contributions: {}, repositories: [], languages: [], activity: [], lastEvent: null };
let refreshTimer = null;
let refreshing = false;
const sockets = new Set();

async function loadState() {
  try { state = JSON.parse(await fs.readFile(STATE_FILE, 'utf8')); }
  catch { await fs.mkdir(DATA_DIR, { recursive: true }); }
}
async function saveState() {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2));
}
function appJwt() {
  const now = Math.floor(Date.now() / 1000);
  return jwt.sign({ iat: now - 30, exp: now + 540, iss: APP_ID }, PRIVATE_KEY, { algorithm: 'RS256' });
}
async function installationToken(installationId = INSTALLATION_ID) {
  if (!APP_ID || !PRIVATE_KEY || !installationId) throw new Error('GitHub App credentials are not configured');
  const response = await fetch(`https://api.github.com/app/installations/${installationId}/access_tokens`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${appJwt()}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10' }
  });
  if (!response.ok) throw new Error(`GitHub installation token failed: ${response.status}`);
  return (await response.json()).token;
}
async function githubRest(url, token) {
  const response = await fetch(url, { headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10', 'User-Agent': 'Saket745-Live-Profile' } });
  if (!response.ok) throw new Error(`GitHub API ${response.status}: ${url}`);
  return response.json();
}
async function githubGraphql(query, variables, token) {
  const response = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10', 'User-Agent': 'Saket745-Live-Profile', 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, variables })
  });
  if (!response.ok) throw new Error(`GitHub GraphQL HTTP ${response.status}`);
  const body = await response.json();
  if (body.errors?.length) throw new Error(body.errors.map(e => e.message).join('; '));
  return body.data;
}
function aggregateLanguages(repos) {
  const totals = new Map();
  for (const repo of repos) for (const [name, bytes] of Object.entries(repo.languageBytes || {})) totals.set(name, (totals.get(name) || 0) + bytes);
  const total = [...totals.values()].reduce((a, b) => a + b, 0);
  return [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([name, bytes]) => ({ name, bytes, percent: total ? Number((bytes * 100 / total).toFixed(1)) : 0 }));
}
async function refreshStats(event = null) {
  if (refreshing) return;
  refreshing = true;
  try {
    const token = await installationToken(event?.installation?.id || INSTALLATION_ID);
    const profile = await githubRest(`https://api.github.com/users/${USERNAME}`, token);
    const repos = await githubRest(`https://api.github.com/users/${USERNAME}/repos?per_page=100&type=owner&sort=updated`, token);
    const repoData = [];
    for (const repo of repos.filter(r => !r.fork)) {
      let languageBytes = {};
      try { languageBytes = await githubRest(repo.languages_url, token); } catch {}
      repoData.push({ name: repo.name, fullName: repo.full_name, url: repo.html_url, description: repo.description, stars: repo.stargazers_count, forks: repo.forks_count, openIssues: repo.open_issues_count, languageBytes, updatedAt: repo.updated_at, isArchived: repo.archived, isPrivate: repo.private });
    }
    const query = `query($login:String!){ user(login:$login){ followers{totalCount} following{totalCount} contributionsCollection { totalCommitContributions totalIssueContributions totalPullRequestContributions totalPullRequestReviewContributions totalRepositoryContributions totalRepositoriesWithContributedCommits contributionCalendar { totalContributions } } } }`;
    const contributions = (await githubGraphql(query, { login: USERNAME }, token)).user.contributionsCollection;
    state = {
      ...state,
      generatedAt: new Date().toISOString(),
      source: 'github', live: true,
      profile: { login: profile.login, name: profile.name, avatar: profile.avatar_url, bio: profile.bio, followers: (await githubGraphql(query, { login: USERNAME }, token)).user.followers.totalCount, following: (await githubGraphql(query, { login: USERNAME }, token)).user.following.totalCount, publicRepos: profile.public_repos, publicGists: profile.public_gists },
      contributions: { total: contributions.contributionCalendar.totalContributions, commits: contributions.totalCommitContributions, issues: contributions.totalIssueContributions, pullRequests: contributions.totalPullRequestContributions, reviews: contributions.totalPullRequestReviewContributions, repositoriesCreated: contributions.totalRepositoryContributions, repositoriesContributedTo: contributions.totalRepositoriesWithContributedCommits },
      repositories: repoData.sort((a, b) => (b.stars - a.stars) || new Date(b.updatedAt) - new Date(a.updatedAt)).slice(0, 12),
      languages: aggregateLanguages(repoData), activity: state.activity,
      lastEvent: event ? { type: event.type, action: event.action || null, repository: event.repository?.full_name || null, receivedAt: new Date().toISOString() } : state.lastEvent
    };
    await saveState();
    broadcast();
  } catch (error) { console.error(error); }
  finally { refreshing = false; }
}
function queueRefresh(event) {
  if (refreshTimer) clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => refreshStats(event), 700);
}
function broadcast() {
  const payload = JSON.stringify({ type: 'stats:update', data: state });
  for (const ws of sockets) if (ws.readyState === 1) ws.send(payload);
}
function validSignature(req) {
  if (!WEBHOOK_SECRET || !req.rawBody) return false;
  const signature = req.headers['x-hub-signature-256'];
  if (typeof signature !== 'string' || !signature.startsWith('sha256=')) return false;
  const expected = `sha256=${crypto.createHmac('sha256', WEBHOOK_SECRET).update(req.rawBody).digest('hex')}`;
  return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}
function summarizeEvent(eventType, body) {
  return { id: crypto.randomUUID(), type: eventType, action: body.action || null, repository: body.repository?.full_name || null, actor: body.sender?.login || body.pusher?.name || null, title: body.pull_request?.title || body.issue?.title || body.repository?.name || null, url: body.pull_request?.html_url || body.issue?.html_url || body.repository?.html_url || null, at: new Date().toISOString() };
}
async function dispatchProfileRefresh(eventType, body) {
  const token = await installationToken(body.installation?.id || INSTALLATION_ID);
  const response = await fetch(`https://api.github.com/repos/${PROFILE_REPO}/dispatches`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10', 'Content-Type': 'application/json', 'User-Agent': 'Saket745-Live-Profile' },
    body: JSON.stringify({ event_type: 'github-event', client_payload: { event: eventType, repository: body.repository?.full_name || null, action: body.action || null } })
  });
  if (!response.ok) throw new Error(`Profile refresh dispatch failed: ${response.status}`);
}

app.get('/api/health', (_req, res) => res.json({ ok: true, live: state.live, generatedAt: state.generatedAt }));
app.get('/api/stats', (_req, res) => res.json(state));
app.post('/webhooks/github', async (req, res) => {
  if (!validSignature(req)) return res.status(401).json({ error: 'invalid signature' });
  const eventType = req.headers['x-github-event'];
  const relevant = new Set(['push', 'pull_request', 'issues', 'issue_comment', 'repository', 'star', 'fork', 'release', 'pull_request_review', 'pull_request_review_comment']);
  if (!relevant.has(eventType)) return res.status(202).json({ ok: true, ignored: eventType });
  state.activity = [summarizeEvent(eventType, req.body), ...state.activity].slice(0, 20);
  state.lastEvent = { type: eventType, action: req.body.action || null, repository: req.body.repository?.full_name || null, receivedAt: new Date().toISOString() };
  broadcast();
  queueRefresh({ ...req.body, type: eventType });
  try { await dispatchProfileRefresh(eventType, req.body); } catch (error) { console.error(error); }
  res.status(202).json({ ok: true });
});

const server = app.listen(PORT, async () => {
  await loadState();
  console.log(`Saket745 live dashboard listening on :${PORT}`);
  if (APP_ID && INSTALLATION_ID && PRIVATE_KEY) await refreshStats();
});
const wss = new WebSocketServer({ server, path: '/ws' });
wss.on('connection', ws => { sockets.add(ws); ws.send(JSON.stringify({ type: 'stats:update', data: state })); ws.on('close', () => sockets.delete(ws)); });
process.on('SIGTERM', () => server.close(() => process.exit(0)));
