/* MUTTA HUB — dev.js（背景設定 + 改密碼）*/
let devToken = '';

document.getElementById('loginBtn').addEventListener('click', doLogin);
document.getElementById('pwdInput').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });

async function doLogin() {
  const pw = document.getElementById('pwdInput').value.trim();
  if (!pw) return;
  try {
    const fd = new FormData(); fd.append('password', pw);
    const res = await fetch('/api/dev/login', { method: 'POST', body: fd });
    if (!res.ok) { document.getElementById('loginErr').textContent = '密碼錯誤'; return; }
    devToken = pw;
    document.getElementById('loginOverlay').style.display = 'none';
    document.getElementById('devApp').style.display = 'block';
    initDev();
  } catch (e) { document.getElementById('loginErr').textContent = '連線錯誤'; }
}

document.getElementById('logoutBtn').addEventListener('click', () => {
  devToken = '';
  document.getElementById('devApp').style.display = 'none';
  document.getElementById('loginOverlay').style.display = 'flex';
  document.getElementById('pwdInput').value = '';
});

async function initDev() {
  const cfg = await (await fetch('/api/config')).json();
  renderBgControls(cfg.background || { type: 'video', darken: 50 });
}

const esc = s => String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// ── 背景設定 ──
let bgType = 'video';
function renderBgControls(bg) {
  bg = bg || { type: 'video', darken: 50 };
  bgType = bg.type || 'video';
  document.querySelectorAll('.bg-type-btn').forEach(b => b.classList.toggle('on', b.dataset.bg === bgType));
  const d = document.getElementById('bgDarken'); if (d) d.value = (bg.darken ?? 50);
  renderVideoLib(bg);
}

// ── 影片庫 ──
function renderVideoLib(bg) {
  const lib = document.getElementById('videoLib'); if (!lib) return;
  const vids = (bg && bg.videos) || []; const active = bg && bg.video;
  lib.innerHTML = '';
  vids.forEach(v => {
    const card = document.createElement('div');
    card.className = 'vid-card' + (v.url === active ? ' active' : '');
    const thumb = v.thumb ? `<img class="vid-thumb" src="${esc(v.thumb)}" alt="">` : `<div class="vid-thumb"></div>`;
    const tag = v.url === active ? `<span class="vid-active-tag">使用中</span>` : '';
    const del = v.id === 'default' ? '' : `<button class="vid-del" data-del="${esc(v.id)}" title="刪除">✕</button>`;
    card.innerHTML = `${thumb}${tag}${del}<div class="vid-name">${esc(v.name || '影片')}</div>`;
    card.addEventListener('click', e => { if (e.target.closest('[data-del]')) return; selectVideo(v.id); });
    lib.appendChild(card);
  });
  lib.querySelectorAll('[data-del]').forEach(b => b.addEventListener('click', e => { e.stopPropagation(); deleteVideo(b.dataset.del); }));
}
async function selectVideo(id) {
  try {
    const res = await fetch('/api/dev/background/select', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Dev-Token': devToken }, body: JSON.stringify({ id }) });
    const d = await res.json().catch(() => ({}));
    if (res.ok) { bgType = 'video'; document.querySelectorAll('.bg-type-btn').forEach(b => b.classList.toggle('on', b.dataset.bg === 'video')); renderVideoLib(d.background); showMsg('bgUpMsg', '✓ 已切換背景，回主頁查看', true); }
    else showMsg('bgUpMsg', d.detail || '切換失敗', false);
  } catch (e) { showMsg('bgUpMsg', '連線錯誤', false); }
}
async function deleteVideo(id) {
  if (!confirm('確定刪除這支影片？')) return;
  try {
    const res = await fetch('/api/dev/background/delete-video', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Dev-Token': devToken }, body: JSON.stringify({ id }) });
    const d = await res.json().catch(() => ({}));
    if (res.ok) { renderVideoLib(d.background); showMsg('bgUpMsg', '已刪除', true); }
    else showMsg('bgUpMsg', d.detail || '刪除失敗', false);
  } catch (e) { showMsg('bgUpMsg', '連線錯誤', false); }
}

document.querySelectorAll('.bg-type-btn').forEach(b => b.addEventListener('click', () => {
  bgType = b.dataset.bg;
  document.querySelectorAll('.bg-type-btn').forEach(x => x.classList.toggle('on', x === b));
}));
document.getElementById('saveBg')?.addEventListener('click', async () => {
  const darken = +document.getElementById('bgDarken').value;
  try {
    const res = await fetch('/api/dev/background', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Dev-Token': devToken },
      body: JSON.stringify({ type: bgType, darken })
    });
    showMsg('bgMsg', res.ok ? '✓ 已儲存，回主頁查看' : '儲存失敗', res.ok);
  } catch (e) { showMsg('bgMsg', '連線錯誤', false); }
});
document.getElementById('uploadBgBtn')?.addEventListener('click', () => {
  const inp = document.createElement('input'); inp.type = 'file'; inp.accept = 'video/mp4,video/*';
  inp.onchange = () => { if (inp.files[0]) uploadBgVideo(inp.files[0]); };
  inp.click();
});
// 在瀏覽器擷取影片畫面當縮圖
function genThumb(file) {
  return new Promise(resolve => {
    const v = document.getElementById('thumbVideo'); const url = URL.createObjectURL(file);
    let done = false; const finish = r => { if (done) return; done = true; try { URL.revokeObjectURL(url); } catch (e) {} resolve(r); };
    v.onloadeddata = () => { try { v.currentTime = Math.min(1.5, (v.duration || 3) / 2); } catch (e) { finish(''); } };
    v.onseeked = () => {
      try {
        const c = document.getElementById('thumbCanvas');
        const w = 360, h = Math.round(w * ((v.videoHeight / v.videoWidth) || 0.5625));
        c.width = w; c.height = h; c.getContext('2d').drawImage(v, 0, 0, w, h);
        finish(c.toDataURL('image/jpeg', 0.7));
      } catch (e) { finish(''); }
    };
    v.onerror = () => finish('');
    v.src = url; v.load();
    setTimeout(() => finish(''), 9000);
  });
}
async function uploadBgVideo(file) {
  if (file.size > 20 * 1024 * 1024) { showMsg('bgUpMsg', `檔案 ${(file.size / 1048576).toFixed(1)}MB 太大，請先壓到 20MB 以下`, false); return; }
  showMsg('bgUpMsg', '產生縮圖中…', true);
  const thumb = await genThumb(file);
  showMsg('bgUpMsg', '上傳中…', true);
  const fd = new FormData();
  fd.append('file', file);
  fd.append('name', file.name.replace(/\.[^.]+$/, '').slice(0, 40));
  fd.append('thumb', thumb || '');
  try {
    const res = await fetch('/api/dev/background/video', { method: 'POST', headers: { 'X-Dev-Token': devToken }, body: fd });
    const data = await res.json().catch(() => ({}));
    if (res.ok) { bgType = 'video'; document.querySelectorAll('.bg-type-btn').forEach(b => b.classList.toggle('on', b.dataset.bg === 'video')); renderVideoLib(data.background); showMsg('bgUpMsg', '✓ 已加入影片庫並選用，回主頁查看', true); }
    else { showMsg('bgUpMsg', data.detail || '上傳失敗', false); }
  } catch (e) { showMsg('bgUpMsg', '連線錯誤', false); }
}

// ── 修改密碼 ──
document.getElementById('savePwd').addEventListener('click', async () => {
  const p1 = document.getElementById('newPwd').value.trim();
  const p2 = document.getElementById('newPwd2').value.trim();
  if (!p1 || p1.length < 6) { showMsg('pwdMsg', '密碼至少 6 碼', false); return; }
  if (p1 !== p2) { showMsg('pwdMsg', '兩次密碼不一致', false); return; }
  try {
    const res = await fetch('/api/dev/change-password', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Dev-Token': devToken },
      body: JSON.stringify({ new: p1 })
    });
    if (res.ok) { devToken = p1; showMsg('pwdMsg', '✓ 密碼已更新', true); document.getElementById('newPwd').value = ''; document.getElementById('newPwd2').value = ''; }
    else showMsg('pwdMsg', '更新失敗', false);
  } catch (e) { showMsg('pwdMsg', '連線錯誤', false); }
});

function showMsg(id, text, ok) {
  const el = document.getElementById(id); if (!el) return;
  el.className = `dev-msg ${ok ? 'ok' : 'err'}`; el.textContent = text;
  setTimeout(() => { el.textContent = ''; }, 3000);
}
