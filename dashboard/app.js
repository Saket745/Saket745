const USER = "Saket745";
const API = "https://api.github.com";
const EVENT_POLL_MS = 60000;
const DATA_REFRESH_MS = 300000;

const profileUrl = `${API}/users/${USER}`;
const reposUrl = `${API}/users/${USER}/repos?per_page=100&type=owner&sort=updated`;
const eventsUrl = `${API}/users/${USER}/events/public?per_page=100`;
const prSearchUrl = `${API}/search/issues?q=author%3A${USER}+is%3Apr&per_page=1`;
const issueSearchUrl = `${API}/search/issues?q=author%3A${USER}+is%3Aissue&per_page=1`;

const stack = [
  ["Py", "Python", "AI / Automation"], ["C+", "C++", "DSA / Systems"],
  ["JS", "JavaScript", "Web / Apps"], ["TS", "TypeScript", "Web / Apps"],
  ["PT", "PyTorch", "Deep Learning"], ["CV", "OpenCV", "Computer Vision"],
  ["Fa", "FastAPI", "Backend"], ["GA", "GitHub Actions", "Automation"]
];

const $ = (id) => document.getElementById(id);
const fmt = (n) => Intl.NumberFormat("en-US", { notation: n > 9999 ? "compact" : "standard", maximumFractionDigits: 1 }).format(n ?? 0);
const ago = (iso) => {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return `${Math.floor(seconds)}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
};
const esc = (s) => String(s ?? "").replace(/[&<>\"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

function setState(kind, text) {
  const dot = $("liveDot");
  dot.className = `dot ${kind === "ok" ? "" : kind === "sync" ? "sync" : "off"}`;
  $("statusText").textContent = text;
  $("statusText").classList.toggle("error", kind === "error");
}

function renderStack() {
  $("stackGrid").innerHTML = stack.map(([icon, name, desc]) => `
    <div class="stack"><div class="icon">${esc(icon)}</div><b>${esc(name)}</b><small>${esc(desc)}</small></div>
  `).join("");
}

async function getJson(url) {
  const r = await fetch(url, { headers: { Accept: "application/vnd.github+json" }, cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function loadCore() {
  const [profile, repos, prs, issues] = await Promise.all([
    getJson(profileUrl),
    getJson(reposUrl),
    getJson(prSearchUrl),
    getJson(issueSearchUrl)
  ]);
  renderProfile(profile, repos, prs.total_count, issues.total_count);
  renderLanguages(repos);
  renderRepos(repos);
}

async function loadEvents() {
  const events = await getJson(eventsUrl);
  renderEvents(events);
  return events;
}

async function syncAll() {
  setState("sync", "Synchronizing with GitHub…");
  try {
    const events = await loadEvents();
    await loadCore();
    estimateEventStats(events);
    $("lastSync").textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setState("ok", `LIVE · event stream checked every ${EVENT_POLL_MS / 1000}s`);
  } catch (err) {
    console.error(err);
    setState("error", "GitHub API unavailable — retrying");
  }
}

function renderProfile(profile, repos, prCount, issueCount) {
  $("repoCount").textContent = fmt(profile.public_repos);
  $("followers").textContent = fmt(profile.followers);
  $("stars").textContent = fmt(repos.reduce((n, r) => n + (r.stargazers_count || 0), 0));
  $("forks").textContent = fmt(repos.reduce((n, r) => n + (r.forks_count || 0), 0));
  $("prs").textContent = fmt(prCount);
  $("issues").textContent = fmt(issueCount);
}

function renderLanguages(repos) {
  const counts = {};
  for (const repo of repos) {
    if (repo.fork || !repo.language) continue;
    counts[repo.language] = (counts[repo.language] || 0) + 1;
  }
  const rows = Object.entries(counts).sort((a,b) => b[1] - a[1]).slice(0, 6);
  const total = rows.reduce((n, [,v]) => n + v, 0);
  $("languageBars").innerHTML = rows.length ? rows.map(([name, value]) => {
    const pct = total ? (value / total) * 100 : 0;
    return `<div class="bar-row"><div class="bar-label">${esc(name)}</div><div class="bar-track"><div class="bar-fill" style="width:${pct.toFixed(1)}%"></div></div><div class="bar-pct">${pct.toFixed(1)}%</div></div>`;
  }).join("") : `<div class="empty">No public repository language data yet.</div>`;
}

function renderRepos(repos) {
  const top = [...repos].filter(r => !r.fork).sort((a,b) => new Date(b.updated_at) - new Date(a.updated_at)).slice(0, 7);
  $("repoUpdated").textContent = `${top.length} shown`;
  $("repos").innerHTML = top.length ? top.map(r => `
    <a class="repo" href="${esc(r.html_url)}" target="_blank" rel="noreferrer" style="text-decoration:none;color:inherit">
      <div><h3>${esc(r.name)}</h3><p>${esc(r.description || "No description yet.")}</p></div>
      <div class="repo-side"><strong>★ ${fmt(r.stargazers_count)}</strong>${esc(r.language || "—")}</div>
    </a>`).join("") : `<div class="empty">No public repositories found.</div>`;
}

function renderEvents(events) {
  const relevant = events.filter(e => ["PushEvent", "PullRequestEvent", "IssuesEvent", "CreateEvent", "ForkEvent", "WatchEvent", "PullRequestReviewEvent", "ReleaseEvent"].includes(e.type)).slice(0, 16);
  const labels = {
    PushEvent: e => `Pushed code to <strong>${esc(e.repo.name.split("/").pop())}</strong>`,
    PullRequestEvent: e => `${esc(e.payload.action)} pull request in <strong>${esc(e.repo.name.split("/").pop())}</strong>`,
    IssuesEvent: e => `${esc(e.payload.action)} issue in <strong>${esc(e.repo.name.split("/").pop())}</strong>`,
    CreateEvent: e => `Created ${esc(e.payload.ref_type)} in <strong>${esc(e.repo.name.split("/").pop())}</strong>`,
    ForkEvent: e => `Forked <strong>${esc(e.repo.name)}</strong>`,
    WatchEvent: e => `Starred <strong>${esc(e.repo.name)}</strong>`,
    PullRequestReviewEvent: e => `${esc(e.payload.action)} review in <strong>${esc(e.repo.name.split("/").pop())}</strong>`,
    ReleaseEvent: e => `${esc(e.payload.action)} release in <strong>${esc(e.repo.name.split("/").pop())}</strong>`
  };
  $("activity").innerHTML = relevant.length ? relevant.map(e => `<div class="event"><span class="event-dot"></span><div class="event-main"><div class="event-title">${labels[e.type]?.(e) || esc(e.type)}</div><div class="event-meta">${esc(e.repo.name)} · ${esc(e.type.replace("Event", ""))}</div></div><span class="event-time">${ago(e.created_at)}</span></div>`).join("") : `<div class="empty">No recent public events available.</div>`;
}

function estimateEventStats(events) {
  const pr = events.filter(e => e.type === "PullRequestEvent").length;
  const issues = events.filter(e => e.type === "IssuesEvent").length;
  $("prs").title = `${$("prs").textContent} total authored PRs; ${pr} recent public PR events visible in the event stream`;
  $("issues").title = `${$("issues").textContent} total authored issues; ${issues} recent public issue events visible in the event stream`;
}

$("refreshBtn").addEventListener("click", syncAll);
renderStack();
syncAll();
setInterval(async () => {
  try {
    const events = await loadEvents();
    estimateEventStats(events);
    $("lastSync").textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setState("ok", `LIVE · event stream checked every ${EVENT_POLL_MS / 1000}s`);
  } catch (e) {
    setState("error", "Event stream temporarily unavailable — retrying");
  }
}, EVENT_POLL_MS);
setInterval(syncAll, DATA_REFRESH_MS);
