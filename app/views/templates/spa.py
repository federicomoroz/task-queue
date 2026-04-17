from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>task-queue // dashboard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=VT323&family=Share+Tech+Mono&display=swap');
  :root{--green:#15ff00;--bg:#080808;--dim:#0a8c00;--card:#0d0d0d;--border:#1a3d00}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--green);font-family:'Share Tech Mono',monospace;min-height:100vh}
  header{border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;gap:16px}
  header h1{font-family:'VT323',monospace;font-size:2rem;letter-spacing:2px}
  header span{color:var(--dim);font-size:.8rem}
  nav{display:flex;gap:0;border-bottom:1px solid var(--border)}
  nav button{background:none;border:none;border-bottom:2px solid transparent;color:var(--dim);cursor:pointer;font-family:'Share Tech Mono',monospace;font-size:.9rem;padding:10px 20px;transition:all .2s}
  nav button:hover{color:var(--green)}
  nav button.active{border-bottom-color:var(--green);color:var(--green)}
  .tab{display:none;padding:24px}
  .tab.active{display:block}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px}
  .card{background:var(--card);border:1px solid var(--border);border-radius:4px;padding:16px}
  .card h3{color:var(--dim);font-size:.75rem;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px}
  .card .val{font-family:'VT323',monospace;font-size:2.5rem}
  table{border-collapse:collapse;width:100%;font-size:.85rem}
  th{color:var(--dim);text-align:left;padding:8px 12px;border-bottom:1px solid var(--border);font-weight:normal;text-transform:uppercase;letter-spacing:1px;font-size:.75rem}
  td{padding:8px 12px;border-bottom:1px solid #111}
  tr:hover td{background:#0d0d0d}
  .badge{border-radius:3px;font-size:.75rem;padding:2px 6px;font-family:'Share Tech Mono',monospace}
  .s-pending{color:#ffcc00;border:1px solid #665200}
  .s-processing{color:#00cfff;border:1px solid #005266}
  .s-completed{color:var(--green);border:1px solid var(--dim)}
  .s-failed{color:#ff3c3c;border:1px solid #660000}
  .s-retrying{color:#ff8800;border:1px solid #663500}
  .form-row{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;align-items:flex-end}
  label{display:flex;flex-direction:column;gap:4px;color:var(--dim);font-size:.8rem}
  input,select,textarea{background:#0d0d0d;border:1px solid var(--border);color:var(--green);font-family:'Share Tech Mono',monospace;font-size:.9rem;padding:8px 10px;border-radius:3px;outline:none;min-width:160px}
  input:focus,select:focus,textarea:focus{border-color:var(--green)}
  textarea{width:100%;min-height:80px;resize:vertical}
  button.btn{background:none;border:1px solid var(--green);color:var(--green);cursor:pointer;font-family:'Share Tech Mono',monospace;font-size:.9rem;padding:8px 18px;border-radius:3px;transition:all .2s}
  button.btn:hover{background:var(--green);color:var(--bg)}
  .msg{margin-top:12px;padding:10px;border-radius:3px;font-size:.85rem}
  .msg.ok{border:1px solid var(--dim);color:var(--green)}
  .msg.err{border:1px solid #660000;color:#ff3c3c}
  .refresh{float:right;color:var(--dim);font-size:.8rem;cursor:pointer}
  .refresh:hover{color:var(--green)}
  .empty{color:var(--dim);padding:24px;text-align:center}
</style>
</head>
<body>
<header>
  <h1>TASK-QUEUE</h1>
  <span>// distributed task processing dashboard</span>
</header>
<nav>
  <button class="active" onclick="showTab('dashboard')">[ dashboard ]</button>
  <button onclick="showTab('enqueue')">[ enqueue ]</button>
  <button onclick="showTab('tasks')">[ tasks ]</button>
  <button onclick="showTab('queues')">[ queues ]</button>
</nav>

<!-- DASHBOARD -->
<div id="dashboard" class="tab active">
  <div class="grid" id="stats-grid">
    <div class="card"><h3>total</h3><div class="val" id="s-total">—</div></div>
    <div class="card"><h3>pending</h3><div class="val" id="s-pending">—</div></div>
    <div class="card"><h3>processing</h3><div class="val" id="s-processing">—</div></div>
    <div class="card"><h3>completed</h3><div class="val" id="s-completed">—</div></div>
    <div class="card"><h3>failed</h3><div class="val" id="s-failed">—</div></div>
  </div>
  <h3 style="color:var(--dim);margin-bottom:12px;font-size:.8rem;letter-spacing:1px">RECENT TASKS</h3>
  <div id="dash-table"></div>
</div>

<!-- ENQUEUE -->
<div id="enqueue" class="tab">
  <h2 style="font-family:VT323,monospace;font-size:1.5rem;margin-bottom:20px;color:var(--dim)">// enqueue task</h2>
  <div class="form-row">
    <label>TYPE
      <select id="e-type" onchange="updatePayloadHint()">
        <option value="echo">echo</option>
        <option value="http_request">http_request</option>
      </select>
    </label>
    <label>QUEUE
      <select id="e-queue">
        <option value="default">default</option>
        <option value="high">high</option>
        <option value="low">low</option>
      </select>
    </label>
    <label>MAX RETRIES
      <input type="number" id="e-retries" value="3" min="0" max="10" style="min-width:80px"/>
    </label>
  </div>
  <label style="margin-bottom:12px">PAYLOAD (JSON)
    <textarea id="e-payload">{"msg": "hello world"}</textarea>
  </label>
  <button class="btn" onclick="enqueueTask()">ENQUEUE &rarr;</button>
  <div id="e-msg" class="msg" style="display:none"></div>
</div>

<!-- TASKS -->
<div id="tasks" class="tab">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <div class="form-row" style="margin:0">
      <label>QUEUE <input id="f-queue" placeholder="all" style="min-width:120px"/></label>
      <label>STATUS
        <select id="f-status">
          <option value="">all</option>
          <option>pending</option><option>processing</option>
          <option>completed</option><option>failed</option><option>retrying</option>
        </select>
      </label>
      <button class="btn" onclick="loadTasks()" style="align-self:flex-end">FILTER</button>
    </div>
    <span class="refresh" onclick="loadTasks()">&#8635; refresh</span>
  </div>
  <div id="tasks-table"></div>
</div>

<!-- QUEUES -->
<div id="queues" class="tab">
  <span class="refresh" onclick="loadQueues()">&#8635; refresh</span>
  <div id="queues-table" style="margin-top:12px"></div>
</div>

<script>
const fmt = (s) => new Date(s).toLocaleString();
const badge = (s) => `<span class="badge s-${s}">${s}</span>`;

function showTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  event.currentTarget.classList.add('active');
  if (name === 'dashboard') loadDashboard();
  if (name === 'tasks') loadTasks();
  if (name === 'queues') loadQueues();
}

function updatePayloadHint() {
  const t = document.getElementById('e-type').value;
  const hints = {
    echo: '{"msg": "hello world"}',
    http_request: '{"method": "GET", "url": "https://httpbin.org/get"}'
  };
  document.getElementById('e-payload').value = hints[t] || '{}';
}

async function enqueueTask() {
  const msgEl = document.getElementById('e-msg');
  msgEl.style.display = 'none';
  let payload;
  try { payload = JSON.parse(document.getElementById('e-payload').value); }
  catch { showMsg('Invalid JSON payload', false); return; }
  const body = {
    type: document.getElementById('e-type').value,
    queue: document.getElementById('e-queue').value,
    max_retries: parseInt(document.getElementById('e-retries').value),
    payload,
  };
  try {
    const r = await fetch('/tasks', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data = await r.json();
    if (r.ok) showMsg(`Task #${data.id} enqueued → ${data.queue} [${data.type}]`, true);
    else showMsg(JSON.stringify(data.detail), false);
  } catch(e) { showMsg(e.message, false); }
}

function showMsg(text, ok) {
  const el = document.getElementById('e-msg');
  el.textContent = text;
  el.className = 'msg ' + (ok ? 'ok' : 'err');
  el.style.display = 'block';
}

async function loadDashboard() {
  const tasks = await fetch('/tasks?limit=500').then(r=>r.json()).catch(()=>[]);
  const counts = {pending:0,processing:0,completed:0,failed:0,retrying:0};
  tasks.forEach(t => { if(counts[t.status]!==undefined) counts[t.status]++; });
  document.getElementById('s-total').textContent = tasks.length;
  Object.keys(counts).forEach(k => {
    const el = document.getElementById('s-'+k);
    if(el) el.textContent = counts[k];
  });
  const recent = tasks.slice(0,10);
  document.getElementById('dash-table').innerHTML = renderTaskTable(recent);
}

async function loadTasks() {
  const q = document.getElementById('f-queue').value;
  const s = document.getElementById('f-status').value;
  let url = '/tasks?limit=200';
  if(q) url += '&queue='+encodeURIComponent(q);
  if(s) url += '&status='+encodeURIComponent(s);
  const tasks = await fetch(url).then(r=>r.json()).catch(()=>[]);
  document.getElementById('tasks-table').innerHTML = renderTaskTable(tasks);
}

function renderTaskTable(tasks) {
  if(!tasks.length) return '<div class="empty">// no tasks found</div>';
  return `<table>
    <thead><tr><th>ID</th><th>TYPE</th><th>QUEUE</th><th>STATUS</th><th>RETRIES</th><th>CREATED</th><th>ERROR</th></tr></thead>
    <tbody>${tasks.map(t=>`<tr>
      <td>#${t.id}</td><td>${t.type}</td><td>${t.queue}</td>
      <td>${badge(t.status)}</td>
      <td>${t.retry_count}/${t.max_retries}</td>
      <td>${fmt(t.created_at)}</td>
      <td style="color:#ff3c3c;max-width:200px;overflow:hidden;text-overflow:ellipsis">${t.error||''}</td>
    </tr>`).join('')}</tbody>
  </table>`;
}

async function loadQueues() {
  const queues = await fetch('/queues').then(r=>r.json()).catch(()=>[]);
  if(!queues.length) { document.getElementById('queues-table').innerHTML='<div class="empty">// no queues</div>'; return; }
  document.getElementById('queues-table').innerHTML = `<table>
    <thead><tr><th>QUEUE</th><th>DEPTH (pending)</th><th>KEY</th></tr></thead>
    <tbody>${queues.map(q=>`<tr>
      <td>${q.name}</td>
      <td><span style="font-family:VT323,monospace;font-size:1.5rem">${q.depth}</span></td>
      <td style="color:var(--dim)">tq:queue:${q.name}</td>
    </tr>`).join('')}</tbody>
  </table>`;
}

loadDashboard();
setInterval(loadDashboard, 5000);
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def spa():
    return HTMLResponse(_HTML)
