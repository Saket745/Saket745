const $ = (id) => document.getElementById(id);
const nf = new Intl.NumberFormat('en-IN');

function fmt(n) { return nf.format(Number(n || 0)); }
function timeAgo(iso) {
  if (!iso) return '—';
  const s = Math.max(1, Math.floor((Date.now() - new Date(iso)) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60); if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}
function esc(s='') {
  return String(s).replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
}

function render(data) {
  const p = data.profile || {}, c = data.contributions || {};
  $('avatar').src = p.avatar || 'https://github.com/Saket745.png';
  $('liveText').textContent = data.live ? 'LIVE' : 'OFFLINE';
  $('liveDot').className = data.live ? 'on' : 'off';
  $('syncTime').textContent = data.generatedAt ? `synced ${timeAgo(data.generatedAt)}` : '—';

  const cards = [
    ['REPOSITORIES', p.publicRepos, 'public'],
    ['FOLLOWERS', p.followers, 'community'],
    ['STARS', (data.repositories || []).reduce((a,r)=>a+(r.stars||0),0), 'tracked repos'],
    ['FORKS', (data.repositories || []).reduce((a,r)=>a+(r.forks||0),0), 'tracked repos'],
    ['CONTRIBUTIONS', c.total, 'current graph'],
    ['PULL REQUESTS', c.pullRequests, 'opened'],
    ['REVIEWS', c.reviews, 'submitted'],
    ['COMMITS', c.commits, 'contributed']
  ];
  $('statsGrid').innerHTML = cards.map(([label,value,sub]) => `<div class="metric glass"><span>${label}</span><strong>${fmt(value)}</strong><small>${sub}</small></div>`).join('');

  const langs = data.languages || [];
  $('languages').innerHTML = langs.length ? langs.map(x => `<div class="lang"><div class="lang-row"><span>${esc(x.name)}</span><span>${x.percent}%</span></div><div class="bar"><i style="width:${Math.min(100,x.percent)}%"></i></div></div>`).join('') : '<div class="empty">Waiting for language data…</div>';

  $('repos').innerHTML = (data.repositories || []).slice(0,8).map(r => `<a class="repo" href="${esc(r.url)}" target="_blank" rel="noreferrer"><div><strong>${esc(r.name)}</strong><small>${esc(r.description || 'No description')}</small></div><span>★ ${fmt(r.stars)}</span></a>`).join('') || '<div class="empty">No repositories found.</div>';

  const events = data.activity || [];
  $('activity').innerHTML = events.length ? events.slice(0,12).map(e => `<a class="event" href="${esc(e.url || '#')}" target="_blank" rel="noreferrer"><span class="event-dot"></span><div><strong>${esc(e.type)}${e.action ? ` · ${esc(e.action)}` : ''}</strong><small>${esc(e.repository || '')}${e.title ? ` — ${esc(e.title)}` : ''}</small></div><time>${timeAgo(e.at)}</time></a>`).join('') : '<div class="empty">Waiting for GitHub events…</div>';
}

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${protocol}://${location.host}/ws`);
  ws.onopen = () => { $('liveText').textContent = 'LIVE'; $('liveDot').className = 'on'; };
  ws.onmessage = (e) => {
    try { const msg = JSON.parse(e.data); if (msg.type === 'stats:update') render(msg.data); } catch {}
  };
  ws.onclose = () => {
    $('liveText').textContent = 'RECONNECTING'; $('liveDot').className = 'off';
    setTimeout(connect, 2500);
  };
}

fetch('/api/stats').then(r => r.json()).then(render).catch(() => {});
connect();
setInterval(() => {
  const stamp = $('syncTime');
  if (stamp && stamp.dataset.last) stamp.textContent = `synced ${timeAgo(stamp.dataset.last)}`;
}, 10000);
