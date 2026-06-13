/* MUTTA HUB — main.js（3×7 字卡 + 1×5 長條 + 編輯器）*/
const $ = s => document.querySelector(s);
const uid = () => Math.random().toString(36).slice(2, 8);
const esc = s => String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const ROWS = 3, COLS = 7, MAXBARS = 5;

let cards = [], bars = [], background = { type: 'video', video: '/static/bg.mp4', darken: 50 };
let token = '', selCard = null, selBar = null;
const editing = () => document.body.classList.contains('editing');

// ── 時鐘 ──
function tick() { const n = new Date(), p = x => String(x).padStart(2, '0'); $('#clock').textContent = `${p(n.getHours())}:${p(n.getMinutes())}:${p(n.getSeconds())}`; }
setInterval(tick, 1000); tick();

// ── logo 連點 5 下進 /dev ──
let logoClicks = 0, logoTimer = null;
$('#hubLogo').addEventListener('click', () => {
  if (editing()) return;
  logoClicks++; clearTimeout(logoTimer);
  if (logoClicks >= 5) { logoClicks = 0; window.location.href = '/dev'; }
  else logoTimer = setTimeout(() => { logoClicks = 0; }, 1200);
});

// ── 載入設定 ──
async function load() {
  try {
    const cfg = await (await fetch('/api/config')).json();
    cards = cfg.cards || []; bars = cfg.bars || [];
    background = cfg.background || background;
  } catch (e) { console.error('載入失敗', e); }
  renderBackground(); renderGrid(); renderBars();
}

// ── 背景 ──
let _bgRaf = null;
function renderBackground() {
  const root = $('#bgRoot'), overlay = $('#bgOverlay');
  if (overlay) overlay.style.opacity = ((background.darken ?? 50) / 100);
  if (_bgRaf) { cancelAnimationFrame(_bgRaf); _bgRaf = null; }
  root.innerHTML = '';
  if (background.type === 'video') {
    const v = document.createElement('video');
    v.className = 'bg-video'; v.autoplay = true; v.muted = true; v.loop = true;
    v.setAttribute('playsinline', ''); v.preload = 'auto';
    v.src = (background.video || '/static/bg.mp4');
    root.appendChild(v); if (v.play) v.play().catch(() => {});
  } else if (background.type === 'shader') {
    const c = document.createElement('canvas'); c.className = 'bg-canvas'; root.appendChild(c); startShader(c);
  }
}
function startShader(canvas) {
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl'); if (!gl) return;
  const f = `precision highp float;uniform vec2 resolution;uniform float time;void main(void){vec2 uv=(gl_FragCoord.xy*2.0-resolution.xy)/min(resolution.x,resolution.y);float t=time*0.05;float lw=0.002;vec3 c=vec3(0.0);for(int j=0;j<3;j++){for(int i=0;i<5;i++){c[j]+=lw*float(i*i)/abs(fract(t-0.01*float(j)+float(i)*0.01)*5.0-length(uv)+mod(uv.x+uv.y,0.2));}}gl_FragColor=vec4(c[0],c[1],c[2],1.0);}`;
  const sh = (ty, s) => { const o = gl.createShader(ty); gl.shaderSource(o, s); gl.compileShader(o); return o; };
  const p = gl.createProgram();
  gl.attachShader(p, sh(gl.VERTEX_SHADER, 'attribute vec2 position;void main(){gl_Position=vec4(position,0.0,1.0);}'));
  gl.attachShader(p, sh(gl.FRAGMENT_SHADER, f)); gl.linkProgram(p); gl.useProgram(p);
  const bf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]), gl.STATIC_DRAW);
  const pl = gl.getAttribLocation(p, 'position'); gl.enableVertexAttribArray(pl); gl.vertexAttribPointer(pl, 2, gl.FLOAT, false, 0, 0);
  const uR = gl.getUniformLocation(p, 'resolution'), uT = gl.getUniformLocation(p, 'time');
  function rz() { const d = window.devicePixelRatio || 1; canvas.width = innerWidth * d; canvas.height = innerHeight * d; gl.viewport(0, 0, canvas.width, canvas.height); gl.uniform2f(uR, canvas.width, canvas.height); }
  window.addEventListener('resize', rz); rz(); let t = 1.0;
  (function lp() { t += 0.05; gl.uniform1f(uT, t); gl.drawArrays(gl.TRIANGLES, 0, 6); _bgRaf = requestAnimationFrame(lp); })();
}

// ── 3×7 字卡網格 ──
const grid = $('#grid');
const cardAt = (r, c) => cards.find(k => k.r === r && k.c === c);
let dragCardId = null;
function renderGrid() {
  grid.innerHTML = '';
  for (let r = 1; r <= ROWS; r++) for (let c = 1; c <= COLS; c++) {
    const cell = document.createElement('div'); cell.className = 'cell'; cell.style.gridArea = `${r}/${c}`; cell.textContent = '＋';
    cell.addEventListener('dragover', e => { e.preventDefault(); cell.classList.add('over'); });
    cell.addEventListener('dragleave', () => cell.classList.remove('over'));
    cell.addEventListener('drop', e => { e.preventDefault(); cell.classList.remove('over'); dropCard(r, c); });
    grid.appendChild(cell);
  }
  cards.forEach(k => {
    if (!editing() && !k.visible) return;
    const a = document.createElement('a');
    a.className = 'card' + (k.visible ? '' : ' hiddenc') + (selCard === k.id ? ' sel' : '');
    a.style.gridArea = `${k.r}/${k.c}`; a.style.setProperty('--a', k.accent);
    a.href = k.href || '#'; if (!editing()) a.target = '_blank'; a.rel = 'noopener';
    a.dataset.id = k.id; a.draggable = editing();
    a.innerHTML = `<div class="mc-top"><div class="mc-glyph">${esc(k.icon)}</div><span class="mc-arrow">↗</span></div>
      <div class="mc-titles"><span class="mc-title">${esc(k.title)}</span><span class="mc-sub">${esc(k.sub)}</span>
      <div class="mc-tags">${k.tag1 ? `<span class="mc-tag">${esc(k.tag1)}</span>` : ''}${k.tag2 ? `<span class="mc-tag">${esc(k.tag2)}</span>` : ''}</div></div>`;
    a.addEventListener('dragstart', () => { dragCardId = k.id; });
    a.addEventListener('click', e => { if (editing()) { e.preventDefault(); selectCard(k.id); } });
    grid.appendChild(a);
  });
}
function dropCard(r, c) {
  const drag = cards.find(k => k.id === dragCardId); if (!drag) return;
  const occ = cardAt(r, c);
  if (occ && occ.id !== drag.id) { occ.r = drag.r; occ.c = drag.c; }
  drag.r = r; drag.c = c; renderGrid(); if (selCard) markSelCard();
}

// ── 1×5 長條 ──
const barRow = $('#barRow');
const barAt = col => bars.find(b => b.col === col);
let dragBarId = null;
function renderBars() {
  barRow.innerHTML = '';
  for (let col = 1; col <= MAXBARS; col++) {
    const cell = document.createElement('div'); cell.className = 'bar-cell'; cell.style.gridColumn = col; cell.textContent = '＋';
    cell.addEventListener('dragover', e => { e.preventDefault(); cell.classList.add('over'); });
    cell.addEventListener('dragleave', () => cell.classList.remove('over'));
    cell.addEventListener('drop', e => { e.preventDefault(); cell.classList.remove('over'); dropBar(col); });
    barRow.appendChild(cell);
  }
  bars.forEach(b => {
    const a = document.createElement('a');
    a.className = 'bar' + (selBar === b.id ? ' sel' : '');
    a.style.gridColumn = b.col; a.style.setProperty('--a', b.accent);
    a.href = b.href || '#'; if (!editing()) a.target = '_blank'; a.rel = 'noopener';
    a.dataset.id = b.id; a.draggable = editing();
    a.innerHTML = `<span class="bar-title">${esc(b.title)}</span><span class="bar-arrow">↗</span>`;
    a.addEventListener('dragstart', () => { dragBarId = b.id; });
    a.addEventListener('click', e => { if (editing()) { e.preventDefault(); selectBar(b.id); } });
    barRow.appendChild(a);
  });
}
function dropBar(col) {
  const drag = bars.find(b => b.id === dragBarId); if (!drag) return;
  const occ = barAt(col);
  if (occ && occ.id !== drag.id) { occ.col = drag.col; }
  drag.col = col; renderBars(); if (selBar) markSelBar();
}

// ── 字卡 inspector ──
const cardInsp = $('#cardInspector');
const cV = $('#cVisible'), cI = $('#cIcon'), cT = $('#cTitle'), cS = $('#cSub'), cT1 = $('#cTag1'), cT2 = $('#cTag2'), cA = $('#cAccent'), cAh = $('#cAccentHex'), cH = $('#cHref');
function markSelCard() { document.querySelectorAll('.card').forEach(el => el.classList.toggle('sel', el.dataset.id === selCard)); }
function selectCard(id) {
  selCard = id; selBar = null; barInsp.classList.remove('show'); markSelCard();
  const k = cards.find(x => x.id === id); if (!k) return;
  cV.checked = k.visible; cI.value = k.icon; cT.value = k.title; cS.value = k.sub; cT1.value = k.tag1; cT2.value = k.tag2;
  cA.value = k.accent; cAh.textContent = k.accent; cH.value = k.href;
  cardInsp.classList.add('show');
}
function bindCard(el, key) { el.addEventListener('input', () => { const k = cards.find(x => x.id === selCard); if (!k) return; k[key] = el.value; renderGrid(); markSelCard(); }); }
cV.addEventListener('change', () => { const k = cards.find(x => x.id === selCard); if (k) { k.visible = cV.checked; renderGrid(); markSelCard(); } });
bindCard(cI, 'icon'); bindCard(cT, 'title'); bindCard(cS, 'sub'); bindCard(cT1, 'tag1'); bindCard(cT2, 'tag2'); bindCard(cH, 'href');
cA.addEventListener('input', () => { const k = cards.find(x => x.id === selCard); if (k) { k.accent = cA.value; cAh.textContent = cA.value; renderGrid(); markSelCard(); } });
$('#cDel').addEventListener('click', () => { cards = cards.filter(x => x.id !== selCard); cardInsp.classList.remove('show'); selCard = null; renderGrid(); toast('已刪除字卡'); });

// ── 長條 inspector ──
const barInsp = $('#barInspector');
const bT = $('#bTitle'), bH = $('#bHref'), bA = $('#bAccent'), bAh = $('#bAccentHex');
function markSelBar() { document.querySelectorAll('.bar').forEach(el => el.classList.toggle('sel', el.dataset.id === selBar)); }
function selectBar(id) {
  selBar = id; selCard = null; cardInsp.classList.remove('show'); markSelBar();
  const b = bars.find(x => x.id === id); if (!b) return;
  bT.value = b.title; bH.value = b.href; bA.value = b.accent; bAh.textContent = b.accent;
  barInsp.classList.add('show');
}
bT.addEventListener('input', () => { const b = bars.find(x => x.id === selBar); if (b) { b.title = bT.value; renderBars(); markSelBar(); } });
bH.addEventListener('input', () => { const b = bars.find(x => x.id === selBar); if (b) { b.href = bH.value; } });
bA.addEventListener('input', () => { const b = bars.find(x => x.id === selBar); if (b) { b.accent = bA.value; bAh.textContent = bA.value; renderBars(); markSelBar(); } });
$('#bDel').addEventListener('click', () => { bars = bars.filter(x => x.id !== selBar); barInsp.classList.remove('show'); selBar = null; renderBars(); toast('已刪除長條'); });

document.querySelectorAll('[data-close]').forEach(x => x.addEventListener('click', () => {
  cardInsp.classList.remove('show'); barInsp.classList.remove('show'); selCard = selBar = null; markSelCard(); markSelBar();
}));

// ── 新增 ──
$('#addCard').addEventListener('click', () => {
  let spot = null; for (let r = 1; r <= ROWS && !spot; r++) for (let c = 1; c <= COLS && !spot; c++) if (!cardAt(r, c)) spot = { r, c };
  if (!spot) { toast('字卡格滿了（3×7）'); return; }
  const k = { id: uid(), r: spot.r, c: spot.c, visible: true, icon: '＋', title: '新字卡', sub: 'SUBTITLE', tag1: '標籤', tag2: '', accent: '#8fb6ff', href: '#' };
  cards.push(k); renderGrid(); selectCard(k.id);
});
$('#addBar').addEventListener('click', () => {
  let col = null; for (let i = 1; i <= MAXBARS; i++) if (!barAt(i)) { col = i; break; }
  if (!col) { toast('長條滿了（最多 5）'); return; }
  const b = { id: uid(), col, title: '新長條', href: '#', accent: '#8fb6ff' };
  bars.push(b); renderBars(); selectBar(b.id);
});

// ── 編輯模式（密碼）──
$('#editFab').addEventListener('click', () => { $('#editLogin').classList.add('show'); $('#elPwd').value = ''; $('#elErr').textContent = ''; $('#elPwd').focus(); });
$('#elCancel').addEventListener('click', () => $('#editLogin').classList.remove('show'));
$('#elPwd').addEventListener('keydown', e => { if (e.key === 'Enter') doEditLogin(); });
$('#elGo').addEventListener('click', doEditLogin);
async function doEditLogin() {
  const pw = $('#elPwd').value.trim(); if (!pw) return;
  try {
    const fd = new FormData(); fd.append('password', pw);
    const res = await fetch('/api/dev/login', { method: 'POST', body: fd });
    if (!res.ok) { $('#elErr').textContent = '密碼錯誤'; return; }
    token = pw; $('#editLogin').classList.remove('show'); enterEdit();
  } catch (e) { $('#elErr').textContent = '連線錯誤'; }
}
function enterEdit() { document.body.classList.add('editing'); renderGrid(); renderBars(); }
function exitEdit() { document.body.classList.remove('editing'); selCard = selBar = null; cardInsp.classList.remove('show'); barInsp.classList.remove('show'); renderGrid(); renderBars(); }
$('#doneBtn').addEventListener('click', exitEdit);

// ── 儲存 ──
$('#saveBtn').addEventListener('click', async () => {
  try {
    const res = await fetch('/api/dev/layout', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Dev-Token': token },
      body: JSON.stringify({ cards, bars })
    });
    if (res.ok) toast('✓ 已儲存'); else if (res.status === 401) toast('登入過期，請重新進入編輯');
    else toast('儲存失敗');
  } catch (e) { toast('連線錯誤'); }
});

// ── 工具 ──
let _tt; function toast(m) { const t = $('#toast'); t.textContent = m; t.classList.add('show'); clearTimeout(_tt); _tt = setTimeout(() => t.classList.remove('show'), 2200); }

load();
