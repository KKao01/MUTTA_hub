/* MUTTA HUB — main.js */
let hubConfig = { links: [], gallery: [], ports: { supermarket: 8000, sf: 8001 } };
let logoClicks = 0, logoTimer = null;

// ── 時鐘 ──
function updateClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2,'0');
  const m = String(now.getMinutes()).padStart(2,'0');
  const s = String(now.getSeconds()).padStart(2,'0');
  document.getElementById('clock').textContent = `${h}:${m}:${s}`;
}
setInterval(updateClock, 1000);
updateClock();

// ── Logo 連點 5 下進開發者模式 ──
document.getElementById('hubLogo').addEventListener('click', () => {
  logoClicks++;
  clearTimeout(logoTimer);
  if (logoClicks >= 5) {
    logoClicks = 0;
    window.location.href = '/dev';
  } else {
    logoTimer = setTimeout(() => { logoClicks = 0; }, 1200);
  }
});

// ── 載入 config ──
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    hubConfig = await res.json();
    renderLinks();
    renderGallery();
  } catch(e) {
    console.error('載入設定失敗', e);
  }
}

// ── 渲染快速連結 ──
function renderLinks() {
  const wrap = document.getElementById('linksWrap');
  wrap.innerHTML = (hubConfig.links || []).map(l => `
    <a class="link-btn" href="${esc(l.url)}" target="_blank" rel="noopener">
      <div class="link-btn-label">${esc(l.label)}</div>
      <div class="link-btn-sub">${esc(l.sub || '')} →</div>
    </a>`).join('');
}

// ── 渲染九宮格 ──
function renderGallery() {
  const grid = document.getElementById('galleryGrid');
  const gallery = hubConfig.gallery || Array(9).fill('');
  grid.innerHTML = gallery.map((url, i) => `
    <div class="gallery-cell">
      ${url
        ? `<img src="${esc(url)}" alt="品牌圖片 ${i+1}">`
        : `<div class="gallery-placeholder">+</div>
           <div class="gallery-placeholder-text">INSERT IMAGE</div>`
      }
    </div>`).join('');
}

// ── Modal ──
function openModal()  { document.getElementById('modeModal').style.display = 'flex'; }
function closeModal(e) {
  if (!e || e.target === document.getElementById('modeModal')) {
    document.getElementById('modeModal').style.display = 'none';
  }
}

function goMode(mode) {
  const urls = {
    supermarket: 'https://muttasupermarket-production.up.railway.app',
    sf: 'https://muttasf-production.up.railway.app'
  };
  const url = urls[mode] || '/';
  window.open(url, '_blank');
  document.getElementById('modeModal').style.display = 'none';
}

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

loadConfig();
