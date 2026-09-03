const USER = "Saket745";
const API = "https://api.github.com";
const POLL_MS = 60000;
const eventsUrl = `${API}/users/${USER}/events/public?per_page=100`;
const reposUrl = `${API}/users/${USER}/repos?per_page=100&type=owner&sort=updated`;
const profileUrl = `${API}/users/${USER}`;
const stack = [
  ["Py", "Python", "AI / Automation"], ["C+", "C++", "DSA / Systems"],
  ["JS", "JavaScript", "Web / Apps"], ["TS", "TypeScript", "Web / Apps"],
  ["PT", "PyTorch", "Deep Learning"], ["CV", "OpenCV", "Computer Vision"],
  ["Fa", "FastAPI", "Backend"], ["GI", "GitHub Actions", "Automation"]
];

const $ = (id) => document.getElementById(id);
const fmt = (n) => Intl.NumberFormat("en-US", { notation: n > 9999 ? "compact" : "standard", maximumFractionDigits: 1 }).format(n ?? 0);
const ago = (iso) => {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
};
const esc = (s) => String(s ?? "").replace(/[&<>\"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

function setState(kind, text) {
  const dot = $("liveDot");
  dot.className = `dot ${kind === "ok" ? "" : kind === "sync" ? "sync" : "off"}`;
  $("statusText").textContent = text;
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

async function syncProfile() {
  setState("sync", "Synchronizing with GitHub…");
  try {
    const [profile, repos, events] = await Promise.all([getJson(profileUrl), getJson(reposUrl), getJson(eventsUrl)]);
    renderProfile(profile, repos);
    renderLanguages(repos);
    renderRepos(repos);
    renderEvents(events);
    $("lastSync").textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setState("ok", `LIVE · polling every ${POLL_MS / 1000}s`);
  } catch (err) {
    console.error(err);
    setState("off", "GitHub API unavailable — retrying");
    $("statusText").classList.add("error");
    $("statusText").textContent = `Sync error: ${err.message}`;
  }
}

function renderProfile(profile, repos) {
  $("repoCount").textContent = fmt(profile.public_repos);
  $("followers").textContent = fmt(profile.followers);
  $("stars").textContent = fmt(repos.reduce((n, r) => n + (r.stargazers_count || 0), 0));
  $("forks").textContent = fmt(repos.reduce((n, r) => n + (r.forks_count || 0), 0));
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
  $("languageSource").textContent = "LIVE";
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
  const relevant = events.filter(e => ["PushEvent", "PullRequestEvent", "IssuesEvent", "CreateEvent", "ForkEvent", "WatchEvent", "PullRequestReviewEvent", "ReleaseEvent"].includes(e.type)).slice(0, 14);
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

function estimateIssueAndPrStats(events) {
  const pr = events.filter(e => e.type === "PullRequestEvent").length;
  const issues = events.filter(e => e.type === "IssuesEvent").length;
  $("prs").textContent = fmt(pr);
  $("issues").textContent = fmt(issues);
}

async function sync() {
  try {
    const events = await getJson(eventsUrl);
    estimateIssueAndPrStats(events);
    renderEvents(events);
    $("lastSync").textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch (e) { console.warn("Event refresh failed", e); }
}

$("refreshBtn").addEventListener("click", syncProfile);
renderStack();
syncProfile();
setInterval(sync, POLL_MS);
setInterval(syncProfile, POLL_MS * 5);
