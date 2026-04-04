/* 分單系統（順豐模式）主頁 JS */
let pdfFile = null, csvFile = null;
let currentJobId = null, currentData = null;

/* ── 贈品預覽切換 ── */
document.getElementById('printGift').addEventListener('change', function() {
  const pg = document.getElementById('previewGift');
  pg.textContent = this.checked ? '梳+C2+F2（盒）+卡' : '（僅顯示分類大字）';
});

/* ── 上傳框設定 ── */
function setupBox(boxId, inputId, nameId, setter, ext) {
  const box = document.getElementById(boxId);
  const inp = document.getElementById(inputId);
  const nm  = document.getElementById(nameId);

  box.addEventListener('click', () => inp.click());

  inp.addEventListener('change', () => {
    const f = inp.files[0];
    if (!f) return;
    setter(f);
    box.classList.add('has-file');
    nm.textContent = f.name;
    nm.style.display = 'block';
    updateBtn();
  });

  box.addEventListener('dragover', e => { e.preventDefault(); box.classList.add('dragover'); });
  box.addEventListener('dragleave', () => box.classList.remove('dragover'));
  box.addEventListener('drop', e => {
    e.preventDefault(); box.classList.remove('dragover');
    const f = [...e.dataTransfer.files].find(f => f.name.toLowerCase().endsWith(ext));
    if (!f) { alert(`請拖入 ${ext.toUpperCase()} 檔案`); return; }
    setter(f);
    box.classList.add('has-file');
    nm.textContent = f.name;
    nm.style.display = 'block';
    updateBtn();
  });
}

setupBox('pdfBox', 'pdfInput', 'pdfName', f => pdfFile = f, '.pdf');
setupBox('csvBox', 'csvInput', 'csvName', f => csvFile = f, '.csv');

function updateBtn() {
  const btn = document.getElementById('processBtn');
  if (pdfFile && csvFile) {
    btn.disabled = false;
    btn.textContent = '開始處理';
  }
}

/* ── 開始處理 ── */
async function startProcess() {
  const fd = new FormData();
  fd.append('pdf_file', pdfFile);
  fd.append('csv_file', csvFile);
  fd.append('print_gift', document.getElementById('printGift').checked ? 'true' : 'false');

  document.getElementById('processBtn').disabled = true;
  document.getElementById('processBtn').textContent = '處理中…';
  document.getElementById('loadingBar').style.display = 'block';
  document.getElementById('resultSection').style.display = 'none';

  try {
    const res = await fetch('/api/process', { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json();
      alert('錯誤：' + (err.detail || '處理失敗'));
      return;
    }
    const data = await res.json();
    currentJobId = data.job_id;
    currentData  = data;
    showResult(data);
  } catch (e) {
    alert('連線錯誤：' + e.message);
  } finally {
    document.getElementById('loadingBar').style.display = 'none';
    document.getElementById('processBtn').disabled = false;
    document.getElementById('processBtn').textContent = '重新處理';
  }
}

/* ── 顯示結果 ── */
function showResult(data) {
  document.getElementById('statTotal').textContent = data.total;
  document.getElementById('statCats').textContent  = data.cat_count;

  document.getElementById('cardsGrid').innerHTML = data.stats.map(s => `
    <div class="card ${s.is_special ? 'special' : ''}" onclick="downloadPDF('${esc(s.cat)}')">
      <div class="card-dl-icon">⬇</div>
      <div class="card-cat">${esc(s.cat)}${s.is_special ? '<span class="card-special-tag">特殊</span>' : ''}</div>
      <div class="card-count">${s.count}</div>
      <div class="card-pages">${s.pages} 頁</div>
      <div class="card-gift">${esc(s.gift_preview)}</div>
    </div>`).join('');

  document.getElementById('resultSection').style.display = 'block';
}

/* ── 下載 ── */
function downloadPDF(cat) {
  const safe = cat.replace(/[/\\ ]+/g, '_').replace(/^_|_$/g, '');
  window.open(`/api/download/${currentJobId}/${safe}.pdf`);
}

function downloadSF() {
  window.open(`/api/download/${currentJobId}/${currentData.excel_name}`);
}

function downloadAll() {
  window.open(`/api/download-all/${currentJobId}`);
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
