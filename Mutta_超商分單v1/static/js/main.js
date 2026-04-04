/* main.js — 超商分單系統主頁 */
const uploadZone  = document.getElementById('uploadZone');
const fileInput   = document.getElementById('fileInput');
const uploadSub   = document.getElementById('uploadSub');
const runBtn      = document.getElementById('runBtn');
const printGift   = document.getElementById('printGift');
const previewGift = document.getElementById('previewGift');
const progressWrap= document.getElementById('progressWrap');
const progressBar = document.getElementById('progressBar');
const loadingBar  = document.getElementById('loadingBar');
const loadingText = document.getElementById('loadingText');
const resultSection = document.getElementById('resultSection');
const statTotal   = document.getElementById('statTotal');
const statCats    = document.getElementById('statCats');
const cardsGrid   = document.getElementById('cardsGrid');
const logArea     = document.getElementById('logArea');
const dlAllBtn    = document.getElementById('dlAllBtn');
const logo        = document.getElementById('logo');
const fileListWrap  = document.getElementById('fileListWrap');
const fileListItems = document.getElementById('fileListItems');

let fileList     = [];   // 累積的 File 物件陣列
let currentJobId = null;
let pollTimer    = null;
let logoClicks   = 0;
let logoTimer    = null;

/* ── 隱藏觸發（logo 點 5 下進開發者頁） ── */
logo.addEventListener('click', () => {
  logoClicks++;
  clearTimeout(logoTimer);
  if (logoClicks >= 5) { logoClicks = 0; window.location.href = '/dev'; }
  else logoTimer = setTimeout(() => { logoClicks = 0; }, 1200);
});

/* ── 列印選項預覽 ── */
printGift.addEventListener('change', () => {
  previewGift.textContent = printGift.checked
    ? '紫撲+C1+F1+乳液各1（盒）'
    : '（僅顯示分類大字）';
});

/* ── 上傳區 ── */
uploadZone.addEventListener('click', () => { fileInput.value = ''; fileInput.click(); });
fileInput.addEventListener('change', () => addFiles([...fileInput.files]));
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault(); uploadZone.classList.remove('drag-over');
  const pdfs = [...e.dataTransfer.files].filter(f => f.name.toLowerCase().endsWith('.pdf'));
  if (!pdfs.length) { alert('請拖入 PDF 檔案'); return; }
  addFiles(pdfs);
});

/* ── 累積加入檔案（同名不重複） ── */
function addFiles(newFiles) {
  const existingNames = new Set(fileList.map(f => f.name));
  const added = newFiles.filter(f => !existingNames.has(f.name));
  const dupes = newFiles.filter(f => existingNames.has(f.name));

  if (dupes.length) {
    alert(`以下檔案已存在，略過：\n${dupes.map(f => f.name).join('\n')}`);
  }
  fileList.push(...added);
  renderFileList();
}

/* ── 渲染檔案清單 ── */
function renderFileList() {
  if (!fileList.length) {
    fileListWrap.style.display = 'none';
    uploadZone.classList.remove('has-file');
    runBtn.disabled = true;
    runBtn.textContent = '請上傳 PDF';
    currentJobId = null;
    return;
  }

  fileListWrap.style.display = 'block';
  uploadZone.classList.add('has-file');
  uploadZone.querySelector('.upload-label').textContent =
    fileList.length === 1 ? fileList[0].name : `已選取 ${fileList.length} 個 PDF`;
  uploadSub.textContent = fileList.length > 1
    ? `共 ${(fileList.reduce((a,f)=>a+f.size,0)/1024/1024).toFixed(1)} MB，合併後處理`
    : `${(fileList[0].size/1024/1024).toFixed(1)} MB`;

  fileListItems.innerHTML = fileList.map((f, i) => `
    <div style="display:flex;align-items:center;justify-content:space-between;
      background:#fff;border:1px solid #E4E2DC;border-radius:8px;
      padding:8px 14px;margin-bottom:6px;font-size:13px;">
      <span style="color:#1A1A2E">📄 ${esc(f.name)}</span>
      <span style="display:flex;align-items:center;gap:12px">
        <span style="color:#A09E98;font-size:11px">${(f.size/1024/1024).toFixed(1)} MB</span>
        <button onclick="removeFile(${i})"
          style="background:none;border:none;color:#EA5455;cursor:pointer;font-size:16px;line-height:1">×</button>
      </span>
    </div>`).join('');

  runBtn.disabled = false;
  runBtn.textContent = fileList.length > 1
    ? `開始分單（${fileList.length} 個檔案）`
    : '開始分單';
  currentJobId = null;  // 檔案變了，需重新上傳
}

function removeFile(idx) {
  fileList.splice(idx, 1);
  renderFileList();
}

function clearAllFiles() {
  fileList = [];
  renderFileList();
}

/* ── 執行分單 ── */
runBtn.addEventListener('click', async () => {
  if (!fileList.length) return;
  runBtn.disabled = true;
  runBtn.textContent = '上傳中…';

  // 先上傳（若尚未上傳或檔案有異動）
  if (!currentJobId) {
    const fd = new FormData();
    fileList.forEach(f => fd.append('files', f));
    try {
      const res = await fetch('/api/upload', { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      currentJobId = data.job_id;
    } catch(e) {
      alert(`上傳失敗：${e.message}`);
      runBtn.disabled = false;
      runBtn.textContent = fileList.length > 1 ? `開始分單（${fileList.length} 個檔案）` : '開始分單';
      return;
    }
  }

  // 執行分單
  runBtn.textContent = '處理中…';
  progressWrap.style.display = 'block';
  progressBar.style.width = '5%';
  loadingBar.style.display = 'block';
  resultSection.style.display = 'none';
  cardsGrid.innerHTML = '';
  logArea.innerHTML = '';

  const fd2 = new FormData();
  fd2.append('print_gift', printGift.checked ? 'true' : 'false');
  await fetch(`/api/process/${currentJobId}`, { method: 'POST', body: fd2 });
  pollTimer = setInterval(pollStatus, 700);
});

async function pollStatus() {
  try {
    const res  = await fetch(`/api/status/${currentJobId}`);
    const data = await res.json();
    if (data.progress != null) progressBar.style.width = data.progress + '%';
    renderLogs(data.logs || []);
    if (data.status === 'done') {
      clearInterval(pollTimer);
      progressBar.style.width = '100%';
      loadingBar.style.display = 'none';
      renderResults(data.results || []);
      runBtn.disabled = false;
      runBtn.textContent = '重新執行';
    } else if (data.status === 'error') {
      clearInterval(pollTimer);
      loadingBar.style.display = 'none';
      alert(`錯誤：${data.error}`);
      runBtn.disabled = false;
      runBtn.textContent = '重新執行';
    }
  } catch(e) {}
}

function renderLogs(logs) {
  logArea.innerHTML = logs.map(l => {
    const cls = l.tag==='ok'?'log-ok':l.tag==='warn'?'log-warn':l.tag==='err'?'log-err':'';
    return `<div><span class="log-ts">${l.ts}</span><span class="${cls}">${esc(l.msg)}</span></div>`;
  }).join('');
  logArea.scrollTop = logArea.scrollHeight;
}

function renderResults(results) {
  const total = results.reduce((a,b) => a+b.count, 0);
  statTotal.textContent = total;
  statCats.textContent  = results.length;
  dlAllBtn.onclick = () => window.open(`/api/download-all/${currentJobId}`);
  cardsGrid.innerHTML = results.map(r => {
    const pct  = Math.max(6, Math.round(r.count/total*100));
    const gift = printGift.checked ? esc(r.gift) : `【${esc(r.cat)}】`;
    return `
      <div class="card ${r.special?'special':''}"
           onclick="window.open('/api/download/${currentJobId}/${encodeURIComponent(r.filename)}')">
        <div class="card-dl-icon">⬇</div>
        <div class="card-cat">${esc(r.cat)}${r.special?'<span class="card-special-tag">特殊</span>':''}</div>
        <div class="card-count">${r.count}</div>
        <div class="card-pages">${r.pages} 頁</div>
        <div class="card-gift">${gift}</div>
        <div class="card-bar" style="width:${pct}%"></div>
      </div>`;
  }).join('');
  resultSection.style.display = 'block';
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
