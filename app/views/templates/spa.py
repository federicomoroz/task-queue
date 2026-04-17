from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>task-queue</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=VT323&family=Share+Tech+Mono&display=swap" rel="stylesheet"/>
  <style>
    :root {
      --green:  #15ff00;
      --dim:    #0a9900;
      --red:    #ff3c3c;
      --yellow: #ffcc00;
      --cyan:   #00ffcc;
      --blue:   #00cfff;
      --orange: #ff8800;
      --bg:     #080808;
      --panel:  #0d0d0d;
      --border: #1a3300;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--green);
      font-family: 'Share Tech Mono', monospace;
      font-size: 14px;
      min-height: 100vh;
    }

    /* ── HEADER ─────────────────────────────────────── */
    header {
      padding: 20px 32px 14px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
    }
    h1 {
      font-family: 'VT323', monospace;
      font-size: 2.8rem;
      letter-spacing: 4px;
      text-shadow: 0 0 14px rgba(21,255,0,0.45);
    }
    .subtitle { color: var(--dim); font-size: 11px; margin-top: 3px; letter-spacing: 1px; }
    .header-right { text-align: right; }
    .clock { font-size: 11px; color: var(--dim); letter-spacing: 1px; }
    .live-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 10px;
      color: var(--dim);
      margin-top: 4px;
      letter-spacing: 1px;
    }
    .live-dot {
      width: 6px; height: 6px;
      background: var(--green);
      border-radius: 50%;
      box-shadow: 0 0 4px var(--green);
      animation: blink 1.4s step-end infinite;
    }
    @keyframes blink { 50% { opacity: 0; } }

    /* ── NAV ────────────────────────────────────────── */
    nav {
      display: flex;
      padding: 0 24px;
      border-bottom: 1px solid var(--border);
    }
    .tab-btn {
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--dim);
      font-family: 'VT323', monospace;
      font-size: 1.3rem;
      letter-spacing: 2px;
      padding: 11px 18px;
      cursor: pointer;
      transition: color .15s, border-color .15s;
    }
    .tab-btn:hover { color: var(--green); }
    .tab-btn.active {
      color: var(--green);
      border-bottom-color: var(--green);
      text-shadow: 0 0 6px rgba(21,255,0,0.35);
    }
    .tab-panel { display: none; padding: 24px 32px; max-width: 1200px; }
    .tab-panel.active { display: block; }

    /* ── STATS GRID ─────────────────────────────────── */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 12px;
      margin-bottom: 28px;
    }
    .stat-card {
      background: var(--panel);
      border: 1px solid var(--border);
      padding: 12px 16px;
      transition: border-color .15s;
      cursor: default;
    }
    .stat-card:hover { border-color: var(--dim); }
    .stat-card .label {
      color: var(--dim);
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 2px;
    }
    .stat-card .value {
      font-family: 'VT323', monospace;
      font-size: 2.4rem;
      line-height: 1;
      margin-top: 3px;
    }

    /* ── SECTION HEADER ─────────────────────────────── */
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }
    h2 { font-family: 'VT323', monospace; font-size: 1.4rem; letter-spacing: 2px; }
    h3 { font-family: 'VT323', monospace; font-size: 1.15rem; letter-spacing: 1px; color: var(--dim); margin-bottom: 10px; }

    /* ── TABLE ──────────────────────────────────────── */
    table { width: 100%; border-collapse: collapse; }
    th {
      color: var(--dim);
      text-align: left;
      padding: 7px 10px;
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      border-bottom: 1px solid var(--border);
      font-weight: normal;
    }
    td {
      padding: 6px 10px;
      border-bottom: 1px solid #0f0f0f;
      font-size: 12px;
      max-width: 220px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    tr:hover td { background: #0b0b0b; }

    /* ── BADGES ─────────────────────────────────────── */
    .badge {
      display: inline-block;
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 2px;
      font-family: 'Share Tech Mono', monospace;
      letter-spacing: 0.5px;
    }
    .s-pending   { color: var(--yellow); border: 1px solid #5a3a00; }
    .s-processing{ color: var(--blue);   border: 1px solid #005266; }
    .s-completed { color: var(--green);  border: 1px solid var(--dim); }
    .s-failed    { color: var(--red);    border: 1px solid #550000; }
    .s-retrying  { color: var(--orange); border: 1px solid #552200; }

    .q-default { color: var(--green); }
    .q-high    { color: var(--cyan);  }
    .q-low     { color: var(--dim);   }

    /* ── BUTTONS ────────────────────────────────────── */
    .btn {
      background: none;
      border: 1px solid var(--green);
      color: var(--green);
      font-family: 'Share Tech Mono', monospace;
      font-size: 11px;
      padding: 6px 14px;
      cursor: pointer;
      transition: background .12s, color .12s, box-shadow .12s;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .btn:hover { background: var(--green); color: var(--bg); box-shadow: 0 0 8px rgba(21,255,0,0.45); }
    .btn:disabled { opacity: .35; cursor: not-allowed; }
    .btn.sm { padding: 3px 8px; font-size: 10px; }
    .btn.cyan  { border-color: var(--cyan);   color: var(--cyan);   }
    .btn.cyan:hover  { background: var(--cyan);   color: var(--bg); box-shadow: 0 0 8px rgba(0,255,204,.45); }
    .btn.yellow{ border-color: var(--yellow); color: var(--yellow); }
    .btn.yellow:hover{ background: var(--yellow); color: var(--bg); box-shadow: 0 0 8px rgba(255,204,0,.45); }
    .btn.orange{ border-color: var(--orange); color: var(--orange); }
    .btn.orange:hover{ background: var(--orange); color: var(--bg); box-shadow: 0 0 8px rgba(255,136,0,.45); }
    .btn.red   { border-color: var(--red);    color: var(--red);    }
    .btn.red:hover   { background: var(--red);    color: var(--bg); box-shadow: 0 0 8px rgba(255,60,60,.45); }

    /* ── FORMS ──────────────────────────────────────── */
    .form-group { margin-bottom: 12px; }
    .form-group label {
      display: block;
      color: var(--dim);
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-bottom: 4px;
    }
    input, select, textarea {
      background: #050505;
      border: 1px solid var(--border);
      color: var(--green);
      font-family: 'Share Tech Mono', monospace;
      font-size: 13px;
      padding: 7px 10px;
      width: 100%;
      outline: none;
      transition: border-color .15s, box-shadow .15s;
    }
    input:focus, select:focus, textarea:focus {
      border-color: var(--green);
      box-shadow: 0 0 5px rgba(21,255,0,0.12);
    }
    textarea { resize: vertical; min-height: 68px; }
    select option { background: var(--bg); }
    .filter-bar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .filter-bar input, .filter-bar select { width: auto; min-width: 120px; }

    /* ── DEMO SCENARIOS ─────────────────────────────── */
    .scenario-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
      margin-bottom: 20px;
    }
    .scenario-card {
      background: var(--panel);
      border: 1px solid var(--border);
      padding: 14px 16px;
      cursor: pointer;
      transition: border-color .15s, box-shadow .15s;
      text-align: left;
    }
    .scenario-card:hover {
      border-color: var(--green);
      box-shadow: 0 0 10px rgba(21,255,0,0.08);
    }
    .scenario-card:disabled { opacity: .4; cursor: not-allowed; }
    .scenario-card .sc-title {
      font-family: 'VT323', monospace;
      font-size: 1.2rem;
      letter-spacing: 1px;
      margin-bottom: 4px;
    }
    .scenario-card .sc-desc { color: var(--dim); font-size: 10px; line-height: 1.5; }
    .scenario-card .sc-badge { float: right; font-size: 9px; color: var(--dim); }

    /* ── LOG PANEL ──────────────────────────────────── */
    .log-panel {
      background: var(--panel);
      border: 1px solid var(--border);
      padding: 10px 14px;
      height: 160px;
      overflow-y: auto;
      font-size: 11px;
      line-height: 1.8;
      scroll-behavior: smooth;
    }
    .log-panel .log-ok  { color: var(--green); }
    .log-panel .log-err { color: var(--red); }
    .log-panel .log-dim { color: var(--dim); }

    /* ── QUEUE BAR ──────────────────────────────────── */
    .queue-bar-wrap {
      background: #0a0a0a;
      border: 1px solid var(--border);
      padding: 14px 18px;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .queue-bar-name {
      font-family: 'VT323', monospace;
      font-size: 1.2rem;
      letter-spacing: 1px;
      min-width: 90px;
    }
    .queue-bar-outer {
      flex: 1;
      background: #0f0f0f;
      border: 1px solid var(--border);
      height: 14px;
      border-radius: 1px;
      overflow: hidden;
    }
    .queue-bar-inner {
      height: 100%;
      background: var(--green);
      transition: width .4s ease;
      box-shadow: 0 0 6px rgba(21,255,0,0.4);
    }
    .queue-bar-depth {
      font-family: 'VT323', monospace;
      font-size: 1.4rem;
      min-width: 40px;
      text-align: right;
    }
    .queue-key { color: var(--dim); font-size: 10px; min-width: 180px; }

    /* ── TOAST ──────────────────────────────────────── */
    #toast {
      position: fixed;
      bottom: 24px; right: 24px;
      background: var(--panel);
      border: 1px solid var(--green);
      color: var(--green);
      font-size: 12px;
      padding: 9px 16px;
      z-index: 200;
      opacity: 0;
      transform: translateY(6px);
      transition: opacity .2s, transform .2s;
      pointer-events: none;
      letter-spacing: 0.5px;
    }
    #toast.show { opacity: 1; transform: translateY(0); }
    #toast.err  { border-color: var(--red);    color: var(--red);    }
    #toast.warn { border-color: var(--yellow); color: var(--yellow); }

    /* ── MISC ───────────────────────────────────────── */
    .loading { color: var(--dim); font-size: 11px; padding: 16px 0; text-align: center; letter-spacing: 2px; }
    .empty   { color: #252525; text-align: center; padding: 18px 0; font-size: 12px; }
    .divider { border: none; border-top: 1px solid var(--border); margin: 20px 0; }
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    @media(max-width: 700px) { .two-col { grid-template-columns: 1fr; } }
  </style>
</head>
<body>

<header>
  <div>
    <h1>&gt; TASK-QUEUE</h1>
    <p class="subtitle">distributed task processing engine &nbsp;|&nbsp; redis broker &nbsp;·&nbsp; sqlite persistence &nbsp;·&nbsp; horizontal worker scaling</p>
  </div>
  <div class="header-right">
    <div class="clock" id="clock">—</div>
    <div class="live-badge"><span class="live-dot"></span> LIVE MONITORING</div>
  </div>
</header>

<nav>
  <button class="tab-btn" data-tab="dashboard" onclick="showTab('dashboard')">DASHBOARD</button>
  <button class="tab-btn" data-tab="enqueue"   onclick="showTab('enqueue')">ENQUEUE</button>
  <button class="tab-btn" data-tab="tasks"     onclick="showTab('tasks')">TASKS</button>
  <button class="tab-btn" data-tab="queues"    onclick="showTab('queues')">QUEUES</button>
</nav>

<!-- ─── DASHBOARD ──────────────────────────────────────────────────────── -->
<div id="tab-dashboard" class="tab-panel">
  <div id="dash-stats" class="stats-grid">
    <div class="stat-card"><div class="label">Total Tasks</div><div class="value" id="s-total">—</div></div>
    <div class="stat-card"><div class="label">Pending</div><div class="value" style="color:var(--yellow)" id="s-pending">—</div></div>
    <div class="stat-card"><div class="label">Processing</div><div class="value" style="color:var(--blue)" id="s-processing">—</div></div>
    <div class="stat-card"><div class="label">Completed</div><div class="value" style="color:var(--green)" id="s-completed">—</div></div>
    <div class="stat-card"><div class="label">Failed</div><div class="value" style="color:var(--red)" id="s-failed">—</div></div>
    <div class="stat-card"><div class="label">Retrying</div><div class="value" style="color:var(--orange)" id="s-retrying">—</div></div>
    <div class="stat-card"><div class="label">Success Rate</div><div class="value" style="color:var(--cyan)" id="s-rate">—</div></div>
  </div>

  <div class="two-col">
    <div>
      <h3>&gt; QUEUE DEPTHS</h3>
      <div id="dash-queues"><p class="loading">LOADING...</p></div>
    </div>
    <div>
      <div class="section-header">
        <h3>&gt; RECENT ACTIVITY</h3>
        <span style="font-size:10px;color:var(--dim)">auto-refresh 2s</span>
      </div>
      <div id="dash-recent"></div>
    </div>
  </div>
</div>

<!-- ─── ENQUEUE ────────────────────────────────────────────────────────── -->
<div id="tab-enqueue" class="tab-panel">
  <div class="section-header">
    <h2>&gt; QUICK SCENARIOS</h2>
    <span style="font-size:10px;color:var(--dim)">one-click demo payloads</span>
  </div>
  <div class="scenario-grid" id="scenario-grid">

    <button class="scenario-card" onclick="runScenario('echo_burst')">
      <span class="sc-badge">5 tasks</span>
      <div class="sc-title" style="color:var(--green)">ECHO BURST</div>
      <div class="sc-desc">5 echo tasks → default queue<br/>each sleeps 1s — watch them process</div>
    </button>

    <button class="scenario-card" onclick="runScenario('http_request')">
      <span class="sc-badge">1 task</span>
      <div class="sc-title" style="color:var(--cyan)">HTTP REQUEST</div>
      <div class="sc-desc">GET httpbin.org/uuid → high queue<br/>real outbound HTTP call</div>
    </button>

    <button class="scenario-card" onclick="runScenario('multi_queue')">
      <span class="sc-badge">6 tasks</span>
      <div class="sc-title" style="color:var(--yellow)">MULTI-QUEUE LOAD</div>
      <div class="sc-desc">2 tasks each to default / high / low<br/>see queue distribution</div>
    </button>

    <button class="scenario-card" onclick="runScenario('stress')">
      <span class="sc-badge">12 tasks</span>
      <div class="sc-title" style="color:var(--orange)">STRESS TEST</div>
      <div class="sc-desc">12 tasks across all queues<br/>mix of echo + http_request</div>
    </button>

  </div>

  <h3>&gt; ENQUEUE LOG</h3>
  <div class="log-panel" id="enqueue-log"><span class="log-dim">— ready. pick a scenario or submit manually —</span></div>

  <hr class="divider"/>

  <h2 style="margin-bottom:14px">&gt; MANUAL SUBMIT</h2>
  <div class="two-col">
    <div>
      <div class="form-group">
        <label>Task Type</label>
        <select id="e-type" onchange="updateHint()">
          <option value="echo">echo</option>
          <option value="http_request">http_request</option>
        </select>
      </div>
      <div class="form-group">
        <label>Queue</label>
        <select id="e-queue">
          <option value="default">default</option>
          <option value="high">high</option>
          <option value="low">low</option>
        </select>
      </div>
      <div class="form-group">
        <label>Max Retries</label>
        <input type="number" id="e-retries" value="3" min="0" max="10"/>
      </div>
    </div>
    <div>
      <div class="form-group">
        <label>Payload (JSON)</label>
        <textarea id="e-payload" rows="5">{"msg": "hello world"}</textarea>
      </div>
    </div>
  </div>
  <button class="btn" onclick="submitManual()">SUBMIT TASK &rarr;</button>
</div>

<!-- ─── TASKS ──────────────────────────────────────────────────────────── -->
<div id="tab-tasks" class="tab-panel">
  <div class="section-header">
    <h2>&gt; TASKS</h2>
    <div class="filter-bar">
      <input id="f-queue"  placeholder="queue (all)" style="min-width:130px"/>
      <select id="f-status">
        <option value="">all statuses</option>
        <option>pending</option>
        <option>processing</option>
        <option>completed</option>
        <option>failed</option>
        <option>retrying</option>
      </select>
      <button class="btn" onclick="loadTasks()">FILTER</button>
      <button class="btn sm" style="color:var(--dim);border-color:var(--dim)" onclick="loadTasks()">&#8635;</button>
    </div>
  </div>
  <div id="tasks-table"><p class="loading">LOADING...</p></div>
</div>

<!-- ─── QUEUES ─────────────────────────────────────────────────────────── -->
<div id="tab-queues" class="tab-panel">
  <div class="section-header">
    <h2>&gt; QUEUE STATUS</h2>
    <button class="btn sm" style="color:var(--dim);border-color:var(--dim)" onclick="loadQueues()">&#8635; REFRESH</button>
  </div>
  <div id="queues-wrap"><p class="loading">LOADING...</p></div>

  <hr class="divider"/>
  <div style="color:var(--dim);font-size:11px;line-height:2">
    <span style="color:var(--green)">Redis key schema:</span>&nbsp; <code>tq:queue:{name}</code> — List (LPUSH enqueue / BRPOP consume)<br/>
    <span style="color:var(--green)">Worker scaling:</span>&nbsp; <code>docker compose up --scale worker=N</code> — N containers compete for same queues<br/>
    <span style="color:var(--green)">Priority:</span>&nbsp; route tasks to <code>high</code> queue for faster processing when workers listen in order
  </div>
</div>

<div id="toast"></div>

<script>
// ── API ─────────────────────────────────────────────────────────────────────
const API = {
  async _req(url, opts = {}) {
    const r = await fetch(url, opts);
    if (r.status === 204) return null;
    const data = await r.json().catch(() => ({ detail: r.statusText }));
    if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  },
  get:  url         => API._req(url),
  post: (url, body) => API._req(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }),
};

// ── Toast ────────────────────────────────────────────────────────────────────
function toast(msg, type = 'ok') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = type === 'err' ? 'err show' : type === 'warn' ? 'warn show' : 'show';
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = ''; }, 3000);
}

// ── Clock ────────────────────────────────────────────────────────────────────
function tickClock() {
  const now = new Date();
  const ts  = now.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  document.getElementById('clock').textContent = ts;
}
setInterval(tickClock, 1000);
tickClock();

// ── Tabs ─────────────────────────────────────────────────────────────────────
const TAB_LOADERS = {
  dashboard: loadDashboard,
  tasks:     loadTasks,
  queues:    loadQueues,
};

function showTab(name, e) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  localStorage.setItem('tq-tab', name);
  TAB_LOADERS[name]?.();
}

// ── Utils ────────────────────────────────────────────────────────────────────
const esc = s => String(s ?? '')
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const fmt = s => s ? new Date(s).toLocaleTimeString() : '—';
const badge = s => `<span class="badge s-${s}">${s}</span>`;
const qcol  = q => `<span class="q-${q||'default'}">${esc(q)}</span>`;

function appendLog(html) {
  const el = document.getElementById('enqueue-log');
  el.innerHTML += html + '\n';
  el.scrollTop = el.scrollHeight;
}

// ── Dashboard ────────────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [tasks, queues] = await Promise.all([
      API.get('/tasks?limit=500'),
      API.get('/queues'),
    ]);

    const counts = { pending: 0, processing: 0, completed: 0, failed: 0, retrying: 0 };
    tasks.forEach(t => { if (counts[t.status] !== undefined) counts[t.status]++; });
    const total = tasks.length;
    const rate  = (counts.completed + counts.failed) > 0
      ? Math.round(counts.completed / (counts.completed + counts.failed) * 100) + '%'
      : 'N/A';

    document.getElementById('s-total').textContent     = total;
    document.getElementById('s-pending').textContent   = counts.pending;
    document.getElementById('s-processing').textContent= counts.processing;
    document.getElementById('s-completed').textContent = counts.completed;
    document.getElementById('s-failed').textContent    = counts.failed;
    document.getElementById('s-retrying').textContent  = counts.retrying;
    document.getElementById('s-rate').textContent      = rate;

    // Queue bars
    const maxDepth = Math.max(1, ...queues.map(q => q.depth));
    document.getElementById('dash-queues').innerHTML = queues.map(q => `
      <div class="queue-bar-wrap">
        <div class="queue-bar-name q-${q.name}">${esc(q.name)}</div>
        <div class="queue-bar-outer">
          <div class="queue-bar-inner" style="width:${Math.max(2, q.depth / maxDepth * 100)}%;${q.depth===0?'background:#1a1a1a;box-shadow:none;':''}"></div>
        </div>
        <div class="queue-bar-depth" style="${q.depth>0?'color:var(--green)':'color:var(--dim)'}">${q.depth}</div>
        <div class="queue-key">tq:queue:${esc(q.name)}</div>
      </div>`).join('');

    // Recent activity
    const recent = tasks.slice(0, 8);
    document.getElementById('dash-recent').innerHTML = recent.length
      ? `<table>
          <thead><tr><th>#</th><th>type</th><th>queue</th><th>status</th><th>time</th></tr></thead>
          <tbody>${recent.map(t => `<tr>
            <td style="color:var(--dim)">${t.id}</td>
            <td>${esc(t.type)}</td>
            <td>${qcol(t.queue)}</td>
            <td>${badge(t.status)}</td>
            <td style="color:var(--dim)">${fmt(t.created_at)}</td>
          </tr>`).join('')}</tbody>
        </table>`
      : '<p class="empty">— no tasks yet. go to ENQUEUE to create some —</p>';

  } catch (e) {
    toast('Dashboard error: ' + e.message, 'err');
  }
}

// ── Scenarios ────────────────────────────────────────────────────────────────
const SCENARIOS = {
  echo_burst: [
    { type: 'echo', queue: 'default', payload: { msg: 'burst-1: the quick brown fox' } },
    { type: 'echo', queue: 'default', payload: { msg: 'burst-2: jumps over the lazy dog' } },
    { type: 'echo', queue: 'default', payload: { msg: 'burst-3: pack my box with five dozen liquor jugs' } },
    { type: 'echo', queue: 'default', payload: { msg: 'burst-4: how vexingly quick daft zebras jump' } },
    { type: 'echo', queue: 'default', payload: { msg: 'burst-5: sphinx of black quartz judge my vow' } },
  ],
  http_request: [
    { type: 'http_request', queue: 'high', payload: { method: 'GET', url: 'https://httpbin.org/uuid' } },
  ],
  multi_queue: [
    { type: 'echo', queue: 'high',    payload: { msg: 'high-priority-1' } },
    { type: 'echo', queue: 'high',    payload: { msg: 'high-priority-2' } },
    { type: 'echo', queue: 'default', payload: { msg: 'normal-1' } },
    { type: 'echo', queue: 'default', payload: { msg: 'normal-2' } },
    { type: 'echo', queue: 'low',     payload: { msg: 'low-priority-1' } },
    { type: 'echo', queue: 'low',     payload: { msg: 'low-priority-2' } },
  ],
  stress: [
    { type: 'echo',         queue: 'high',    payload: { msg: 'stress-h1' } },
    { type: 'echo',         queue: 'high',    payload: { msg: 'stress-h2' } },
    { type: 'echo',         queue: 'high',    payload: { msg: 'stress-h3' } },
    { type: 'echo',         queue: 'default', payload: { msg: 'stress-d1' } },
    { type: 'echo',         queue: 'default', payload: { msg: 'stress-d2' } },
    { type: 'echo',         queue: 'default', payload: { msg: 'stress-d3' } },
    { type: 'echo',         queue: 'default', payload: { msg: 'stress-d4' } },
    { type: 'echo',         queue: 'low',     payload: { msg: 'stress-l1' } },
    { type: 'echo',         queue: 'low',     payload: { msg: 'stress-l2' } },
    { type: 'http_request', queue: 'high',    payload: { method: 'GET', url: 'https://httpbin.org/get' } },
    { type: 'http_request', queue: 'default', payload: { method: 'GET', url: 'https://httpbin.org/uuid' } },
    { type: 'http_request', queue: 'high',    payload: { method: 'POST', url: 'https://httpbin.org/post', body: { demo: true } } },
  ],
};

async function runScenario(name) {
  const tasks = SCENARIOS[name];
  if (!tasks) return;

  // Disable all scenario buttons
  document.querySelectorAll('.scenario-card').forEach(b => b.disabled = true);

  const label = name.replace('_', ' ').toUpperCase();
  appendLog(`<span class="log-dim">─── ${label} (${tasks.length} tasks) ───────────────────────</span>`);

  let ok = 0, fail = 0;
  for (const t of tasks) {
    try {
      const res = await API.post('/tasks', { ...t, max_retries: 3 });
      appendLog(`<span class="log-ok">  ✓ #${res.id} ${t.type} → ${t.queue}</span><span class="log-dim"> ${JSON.stringify(t.payload).slice(0,50)}</span>`);
      ok++;
    } catch (e) {
      appendLog(`<span class="log-err">  ✗ ${t.type} → ${t.queue} — ${esc(e.message)}</span>`);
      fail++;
    }
  }

  appendLog(`<span class="log-dim">  done: ${ok} queued${fail ? ', ' + fail + ' failed' : ''} — switch to DASHBOARD to watch</span>\n`);
  toast(`${ok} task${ok !== 1 ? 's' : ''} enqueued`, ok > 0 ? 'ok' : 'err');

  document.querySelectorAll('.scenario-card').forEach(b => b.disabled = false);
}

// ── Manual submit ─────────────────────────────────────────────────────────────
function updateHint() {
  const hints = {
    echo: '{"msg": "hello world"}',
    http_request: '{"method": "GET", "url": "https://httpbin.org/uuid"}',
  };
  document.getElementById('e-payload').value = hints[document.getElementById('e-type').value] || '{}';
}

async function submitManual() {
  let payload;
  try { payload = JSON.parse(document.getElementById('e-payload').value); }
  catch { toast('Invalid JSON payload', 'err'); return; }

  const body = {
    type:        document.getElementById('e-type').value,
    queue:       document.getElementById('e-queue').value,
    max_retries: parseInt(document.getElementById('e-retries').value),
    payload,
  };

  try {
    const res = await API.post('/tasks', body);
    appendLog(`<span class="log-ok">  ✓ #${res.id} ${res.type} → ${res.queue}</span> <span class="log-dim">${JSON.stringify(payload).slice(0,60)}</span>`);
    toast(`Task #${res.id} enqueued → ${res.queue}`);
  } catch (e) {
    appendLog(`<span class="log-err">  ✗ ${esc(e.message)}</span>`);
    toast(e.message, 'err');
  }
}

// ── Tasks ────────────────────────────────────────────────────────────────────
async function loadTasks() {
  const q = document.getElementById('f-queue')?.value || '';
  const s = document.getElementById('f-status')?.value || '';
  let url = '/tasks?limit=200';
  if (q) url += '&queue=' + encodeURIComponent(q);
  if (s) url += '&status=' + encodeURIComponent(s);

  document.getElementById('tasks-table').innerHTML = '<p class="loading">LOADING...</p>';
  try {
    const tasks = await API.get(url);
    document.getElementById('tasks-table').innerHTML = tasks.length
      ? `<table>
          <thead>
            <tr><th>#</th><th>type</th><th>queue</th><th>status</th>
            <th>retries</th><th>created</th><th>updated</th><th>error</th></tr>
          </thead>
          <tbody>${tasks.map(t => `<tr>
            <td style="color:var(--dim)">${t.id}</td>
            <td>${esc(t.type)}</td>
            <td>${qcol(t.queue)}</td>
            <td>${badge(t.status)}</td>
            <td style="color:${t.retry_count>0?'var(--orange)':'var(--dim)'}">${t.retry_count}/${t.max_retries}</td>
            <td style="color:var(--dim)">${fmt(t.created_at)}</td>
            <td style="color:var(--dim)">${fmt(t.updated_at)}</td>
            <td style="color:var(--red);max-width:180px" title="${esc(t.error||'')}">${esc((t.error||'').slice(0,40))}</td>
          </tr>`).join('')}</tbody>
        </table>`
      : '<p class="empty">— no tasks match the current filter —</p>';
  } catch (e) {
    document.getElementById('tasks-table').innerHTML = `<p style="color:var(--red);padding:10px">${esc(e.message)}</p>`;
  }
}

// ── Queues ───────────────────────────────────────────────────────────────────
async function loadQueues() {
  document.getElementById('queues-wrap').innerHTML = '<p class="loading">LOADING...</p>';
  try {
    const queues = await API.get('/queues');
    const maxDepth = Math.max(1, ...queues.map(q => q.depth));
    document.getElementById('queues-wrap').innerHTML = queues.map(q => `
      <div class="queue-bar-wrap">
        <div class="queue-bar-name q-${q.name}">${esc(q.name)}</div>
        <div class="queue-bar-outer" style="flex:1">
          <div class="queue-bar-inner" style="width:${Math.max(2, q.depth / maxDepth * 100)}%;${q.depth===0?'background:#1a1a1a;box-shadow:none;':''}"></div>
        </div>
        <div class="queue-bar-depth" style="${q.depth>0?'color:var(--green)':'color:var(--dim)'}">${q.depth}</div>
        <div class="queue-key">tq:queue:${esc(q.name)}</div>
      </div>`).join('') || '<p class="empty">— no queues configured —</p>';
  } catch (e) {
    document.getElementById('queues-wrap').innerHTML = `<p style="color:var(--red);padding:10px">${esc(e.message)}</p>`;
  }
}

// ── Auto-refresh dashboard ────────────────────────────────────────────────────
setInterval(() => {
  if (document.getElementById('tab-dashboard').classList.contains('active')) {
    loadDashboard();
  }
}, 2000);

// ── Init ─────────────────────────────────────────────────────────────────────
showTab(localStorage.getItem('tq-tab') || 'dashboard');
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def spa():
    return HTMLResponse(_HTML)
