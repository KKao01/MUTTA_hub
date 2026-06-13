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

// ── 背景設定 ──
let bgType = 'video';
function renderBgControls(bg) {
  bg = bg || { type: 'video', darken: 50 };
  bgType = bg.type || 'video';
  document.querySelectorAll('.bg-type-btn').forEach(b => b.classList.toggle('on', b.dataset.bg === bgType));
  const d = document.getElementById('bgDarken'); if (d) d.value = (bg.darken ?? 50);
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
async function uploadBgVideo(file) {
  if (file.size > 20 * 1024 * 1024) { showMsg('bgUpMsg', `檔案 ${(file.size / 1048576).toFixed(1)}MB 太大，請先壓到 20MB 以下`, false); return; }
  showMsg('bgUpMsg', '上傳中…', true);
  const fd = new FormData(); fd.append('file', file);
  try {
    const res = await fetch('/api/dev/background/video', { method: 'POST', headers: { 'X-Dev-Token': devToken }, body: fd });
    const data = await res.json().catch(() => ({}));
    if (res.ok) { showMsg('bgUpMsg', `✓ 已更新（${(data.size / 1048576).toFixed(1)}MB），回主頁查看`, true); }
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
