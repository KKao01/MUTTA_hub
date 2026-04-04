/* MUTTA HUB — dev.js */
let devToken = '';

// ── 登入 ──
document.getElementById('loginBtn').addEventListener('click', doLogin);
document.getElementById('pwdInput').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });

async function doLogin() {
  const pw = document.getElementById('pwdInput').value.trim();
  if (!pw) return;
  try {
    const fd = new FormData();
    fd.append('password', pw);
    const res = await fetch('/api/dev/login', { method: 'POST', body: fd });
    if (!res.ok) { document.getElementById('loginErr').textContent = '密碼錯誤'; return; }
    devToken = pw;
    document.getElementById('loginOverlay').style.display = 'none';
    document.getElementById('devApp').style.display = 'block';
    initDev();
  } catch(e) {
    document.getElementById('loginErr').textContent = '連線錯誤';
  }
}

document.getElementById('logoutBtn').addEventListener('click', () => {
  devToken = '';
  document.getElementById('devApp').style.display = 'none';
  document.getElementById('loginOverlay').style.display = 'flex';
  document.getElementById('pwdInput').value = '';
});

// ── 初始化開發者介面 ──
async function initDev() {
  const res = await fetch('/api/config');
  const cfg = await res.json();
  renderLinksEditor(cfg.links || []);
  renderDevGallery(cfg.gallery || Array(9).fill(''));
}

// ── 快速連結編輯 ──
function renderLinksEditor(links) {
  const container = document.getElementById('linksEditor');
  while (links.length < 2) links.push({ label: '', url: '', sub: '' });
  container.innerHTML = links.map((l, i) => `
    <div class="link-editor-row">
      <input class="dev-input" id="link_label_${i}" value="${esc(l.label)}" placeholder="按鈕名稱">
      <input class="dev-input" id="link_url_${i}"   value="${esc(l.url)}"   placeholder="https://...">
    </div>`).join('');
}

document.getElementById('saveLinks').addEventListener('click', async () => {
  const links = [0, 1].map(i => {
    const label = document.getElementById(`link_label_${i}`)?.value.trim() || '';
    const url   = document.getElementById(`link_url_${i}`)?.value.trim()   || '';
    const sub   = url.replace(/^https?:\/\//, '').split('/')[0];
    return { label, url, sub };
  });
  try {
    const res = await fetch('/api/dev/links', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Dev-Token': devToken },
      body: JSON.stringify(links)
    });
    showMsg('linksMsg', res.ok ? '✓ 已儲存' : '儲存失敗', res.ok);
  } catch(e) {
    showMsg('linksMsg', '連線錯誤', false);
  }
});

// ── 九宮格圖片編輯 ──
function renderDevGallery(gallery) {
  const grid = document.getElementById('devGalleryGrid');
  grid.innerHTML = gallery.map((url, i) => `
    <div class="dev-gallery-cell" id="dev_cell_${i}" onclick="cellClick(${i})">
      ${url ? `<img src="${esc(url)}" alt="">
               <div class="cell-overlay">
                 <div class="cell-overlay-text">點擊刪除</div>
               </div>` :
               `<div class="cell-add">+</div>
                <div class="cell-add-text">上傳圖片</div>`}
    </div>`).join('');
}

function cellClick(idx) {
  const cell = document.getElementById(`dev_cell_${idx}`);
  const hasImg = cell.querySelector('img');
  if (hasImg) {
    if (!confirm('刪除此圖片？')) return;
    deleteGallery(idx);
  } else {
    const inp = document.createElement('input');
    inp.type = 'file'; inp.accept = 'image/*';
    inp.onchange = () => { if (inp.files[0]) uploadGallery(idx, inp.files[0]); };
    inp.click();
  }
}

async function uploadGallery(idx, file) {
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch(`/api/dev/gallery/${idx}`, {
      method: 'POST',
      headers: { 'X-Dev-Token': devToken },
      body: fd
    });
    const data = await res.json();
    if (data.ok) {
      const cell = document.getElementById(`dev_cell_${idx}`);
      cell.innerHTML = `<img src="${data.url}?t=${Date.now()}" alt="">
        <div class="cell-overlay"><div class="cell-overlay-text">點擊刪除</div></div>`;
    }
  } catch(e) { alert('上傳失敗'); }
}

async function deleteGallery(idx) {
  try {
    await fetch(`/api/dev/gallery/${idx}`, {
      method: 'DELETE',
      headers: { 'X-Dev-Token': devToken }
    });
    const cell = document.getElementById(`dev_cell_${idx}`);
    cell.innerHTML = `<div class="cell-add">+</div><div class="cell-add-text">上傳圖片</div>`;
  } catch(e) { alert('刪除失敗'); }
}

// ── 修改密碼 ──
document.getElementById('savePwd').addEventListener('click', async () => {
  const p1 = document.getElementById('newPwd').value.trim();
  const p2 = document.getElementById('newPwd2').value.trim();
  if (!p1 || p1.length < 6) { showMsg('pwdMsg', '密碼至少 6 碼', false); return; }
  if (p1 !== p2)             { showMsg('pwdMsg', '兩次密碼不一致', false); return; }
  try {
    const res = await fetch('/api/dev/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Dev-Token': devToken },
      body: JSON.stringify({ new: p1 })
    });
    if (res.ok) {
      devToken = p1;
      showMsg('pwdMsg', '✓ 密碼已更新', true);
      document.getElementById('newPwd').value = '';
      document.getElementById('newPwd2').value = '';
    } else {
      showMsg('pwdMsg', '更新失敗', false);
    }
  } catch(e) { showMsg('pwdMsg', '連線錯誤', false); }
});

// ── 工具 ──
function showMsg(id, text, ok) {
  let el = document.getElementById(id);
  if (!el) {
    el = document.createElement('div');
    el.id = id; el.className = 'dev-msg';
    document.getElementById('savePwd')?.parentElement?.insertBefore(el, document.getElementById('savePwd'));
  }
  el.className = `dev-msg ${ok ? 'ok' : 'err'}`;
  el.textContent = text;
  setTimeout(() => { el.textContent = ''; }, 3000);
}

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
