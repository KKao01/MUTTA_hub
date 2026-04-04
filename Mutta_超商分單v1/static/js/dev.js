/* dev.js */
let devToken = sessionStorage.getItem('devToken') || '';
let productMap = {};
let giftRules  = {};
let editingProductKey = null;
let editingGiftCat    = null;
let importRows = [];

const loginOverlay = document.getElementById('loginOverlay');
const devApp       = document.getElementById('devApp');
const pwdInput     = document.getElementById('pwdInput');
const loginBtn     = document.getElementById('loginBtn');
const loginError   = document.getElementById('loginError');

async function tryLogin() {
  const pwd = pwdInput.value.trim(); if (!pwd) return;
  loginError.textContent = '';
  const fd = new FormData(); fd.append('password', pwd);
  try {
    const res = await fetch('/api/dev/login', { method:'POST', body:fd });
    if (res.ok) {
      devToken=pwd; sessionStorage.setItem('devToken',pwd);
      loginOverlay.style.display='none'; devApp.style.display='flex'; loadConfig();
    } else { loginError.textContent='密碼錯誤，請重試'; pwdInput.value=''; pwdInput.focus(); }
  } catch { loginError.textContent='無法連接伺服器'; }
}
loginBtn.addEventListener('click', tryLogin);
pwdInput.addEventListener('keydown', e=>{ if(e.key==='Enter') tryLogin(); });

if (devToken) {
  fetch('/api/dev/config',{headers:{'X-Dev-Token':devToken}})
    .then(r=>{ if(r.ok){loginOverlay.style.display='none';devApp.style.display='flex';loadConfig();}
               else{devToken='';sessionStorage.removeItem('devToken');} }).catch(()=>{});
}

document.getElementById('logoutBtn').addEventListener('click',()=>{
  devToken=''; sessionStorage.removeItem('devToken');
  devApp.style.display='none'; loginOverlay.style.display='flex'; pwdInput.value='';
});

document.querySelectorAll('.dev-nav-item').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.dev-nav-item').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.dev-tab').forEach(t=>t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-'+btn.dataset.tab).classList.add('active');
  });
});

async function loadConfig() {
  const res = await fetch('/api/dev/config',{headers:{'X-Dev-Token':devToken}});
  const cfg = await res.json();
  productMap = cfg.product_map || {};
  giftRules  = cfg.gift_rules  || {};
  renderProductTable();
  renderGiftTable();
}

/* ══ 商品對照：商品名稱 | 品項 | 分類名稱 | 操作 ══ */
function renderProductTable() {
  const tbody = document.getElementById('priceTableBody');
  const entries = Object.entries(productMap).sort((a,b)=>{
    const [an,ai]=a[0].split('|||'); const [bn,bi]=b[0].split('|||');
    return an.localeCompare(bn,'zh-TW')||(ai||'').localeCompare(bi||'','zh-TW');
  });
  tbody.innerHTML = entries.length===0
    ? `<tr><td colspan="4" style="text-align:center;color:#5A5878;padding:24px">尚無資料，請上傳 Excel 匯入</td></tr>`
    : entries.map(([key,info])=>{
        const [name,items]=key.split('|||');
        return `<tr>
          <td style="font-size:12px">${escHtml(name)}</td>
          <td style="font-size:12px;color:#A89EEF">${escHtml(items||'—')}</td>
          <td>${escHtml(info.kind)}</td>
          <td style="white-space:nowrap">
            <button class="tbl-edit-btn" onclick='openProductEdit(${JSON.stringify(key)})'>編輯</button>
            <button class="tbl-del-btn"  onclick='delProduct(${JSON.stringify(key)})'>刪除</button>
          </td></tr>`;
      }).join('');
}

/* ── 新增/編輯 modal ── */
const editModal = document.getElementById('editModal');

document.getElementById('addRowBtn').addEventListener('click',()=>{
  editingProductKey=null;
  document.getElementById('modalTitle').textContent='新增商品對照';
  document.getElementById('editPrice').value='';
  document.getElementById('editItems').value='';
  document.getElementById('editKind').value='';
  document.getElementById('editMsg').textContent='';
  editModal.style.display='flex'; document.getElementById('editPrice').focus();
});

function openProductEdit(key){
  editingProductKey=key;
  const [name,items]=key.split('|||');
  document.getElementById('modalTitle').textContent='編輯商品對照';
  document.getElementById('editPrice').value=name;
  document.getElementById('editItems').value=items||'';
  document.getElementById('editKind').value=productMap[key]?.kind||'';
  document.getElementById('editMsg').textContent='';
  editModal.style.display='flex'; document.getElementById('editKind').focus();
}

document.getElementById('cancelEdit').addEventListener('click',()=>editModal.style.display='none');
editModal.addEventListener('click',e=>{if(e.target===editModal)editModal.style.display='none';});

document.getElementById('saveEdit').addEventListener('click',async()=>{
  const name  = document.getElementById('editPrice').value.trim();
  const items = document.getElementById('editItems').value.trim();
  const kind  = document.getElementById('editKind').value.trim();
  const msg   = document.getElementById('editMsg');
  if (!name){msg.textContent='商品名稱不能空白';return;}
  if (!kind){msg.textContent='分類名稱不能空白';return;}
  const newKey=`${name}|||${items}`;
  if (editingProductKey && editingProductKey!==newKey) delete productMap[editingProductKey];
  productMap[newKey]={kind};
  await saveProductMap(); editModal.style.display='none';
});

async function delProduct(key){
  const [name]=key.split('|||');
  if(!confirm(`確定刪除「${name}」的對照？`))return;
  delete productMap[key]; await saveProductMap();
}

async function saveProductMap(){
  await fetch('/api/dev/product-map',{
    method:'POST',headers:{'X-Dev-Token':devToken,'Content-Type':'application/json'},
    body:JSON.stringify(productMap)
  });
  renderProductTable();
}

/* ══ Excel 匯入 ══ */
document.getElementById('importLabel').addEventListener('click', () => {
  document.getElementById('excelInput').value = '';
  document.getElementById('excelInput').click();
});

document.getElementById('excelInput').addEventListener('change', handleExcelFile);

async function handleExcelFile(){
  const file=this.files[0]; if(!file)return;
  const lbl=document.getElementById('importLabel');
  lbl.textContent='解析中...';
  const fd=new FormData(); fd.append('file',file);
  try {
    const res=await fetch('/api/dev/parse-excel',{method:'POST',headers:{'X-Dev-Token':devToken},body:fd});
    lbl.innerHTML=`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>匯入 Excel 更新`;
    if(!res.ok){const e=await res.json();alert(e.detail||'解析失敗');return;}
    const data=await res.json();
    showImportPreview(file.name,data.rows,data.total);
  } catch(e){lbl.textContent='匯入 Excel 更新';alert('匯入失敗：'+e.message);}
}

function showImportPreview(filename,rows,total){
  importRows=rows;
  document.getElementById('importPreview').style.display='block';
  document.getElementById('mainTableWrap').style.display='none';
  const newCount=rows.filter(r=>r.is_new).length;
  document.getElementById('importPreviewTitle').textContent=
    `解析完成：${total} 筆商品組合（${newCount} 筆新增）`;
  document.getElementById('importPreviewSub').textContent=
    `來源：${filename}　確認後將完全取代現有對照表`;
  document.getElementById('importTableBody').innerHTML=rows.map((r,i)=>`
    <tr>
      <td style="font-size:12px">${escHtml(r.product_name)}</td>
      <td style="font-size:12px;color:#A89EEF">${escHtml(r.items)||'—'}</td>
      <td><input class="kind-input ${r.kind?'has-value':''}" data-idx="${i}"
           value="${escHtml(r.kind)}" placeholder="填入分類名稱"
           oninput="this.classList.toggle('has-value',!!this.value)"></td>
      <td>${r.is_new?'<span class="badge-new">新增</span>':'<span class="badge-existing">已有</span>'}</td>
    </tr>`).join('');
}

document.getElementById('cancelImport').addEventListener('click',()=>{
  document.getElementById('importPreview').style.display='none';
  document.getElementById('mainTableWrap').style.display='block';
});

document.getElementById('confirmImport').addEventListener('click',async()=>{
  const newMap={};
  document.querySelectorAll('#importTableBody input[data-idx]').forEach(input=>{
    const r=importRows[parseInt(input.dataset.idx)];
    const kind=input.value.trim()||r.kind;
    if(kind) newMap[r.key]={kind};
  });
  productMap=newMap; await saveProductMap();
  document.getElementById('importPreview').style.display='none';
  document.getElementById('mainTableWrap').style.display='block';
});

/* ══ 贈品規則 ══ */
function renderGiftTable(){
  const tbody=document.getElementById('giftTableBody');
  const entries=Object.entries(giftRules).sort((a,b)=>a[0].localeCompare(b[0],'zh-TW'));
  tbody.innerHTML=entries.length===0
    ? `<tr><td colspan="4" style="text-align:center;color:#5A5878;padding:24px">尚無贈品規則</td></tr>`
    : entries.map(([cat,rule])=>{
        const same=rule.female===rule.male;
        return `<tr>
          <td><strong>${escHtml(cat)}</strong></td>
          <td style="font-size:12px">${escHtml(rule.female||'')}</td>
          <td style="font-size:12px;${same?'color:#5A5878':''}">${same?'（同女性）':escHtml(rule.male||'')}</td>
          <td>
            <button class="tbl-edit-btn" onclick='openGiftEdit(${JSON.stringify(cat)})'>編輯</button>
            <button class="tbl-del-btn"  onclick='delGift(${JSON.stringify(cat)})'>刪除</button>
          </td></tr>`;
      }).join('');
}

const giftModal=document.getElementById('giftModal');
document.getElementById('addGiftBtn').addEventListener('click',()=>{
  editingGiftCat=null;
  document.getElementById('giftModalTitle').textContent='新增贈品規則';
  document.getElementById('giftCat').value=''; document.getElementById('giftFemale').value='';
  document.getElementById('giftMale').value=''; document.getElementById('giftEditMsg').textContent='';
  giftModal.style.display='flex'; document.getElementById('giftCat').focus();
});

function openGiftEdit(cat){
  editingGiftCat=cat;
  document.getElementById('giftModalTitle').textContent='編輯贈品規則';
  const rule=giftRules[cat]||{};
  document.getElementById('giftCat').value=cat;
  document.getElementById('giftFemale').value=rule.female||'';
  document.getElementById('giftMale').value=rule.female===rule.male?'':(rule.male||'');
  document.getElementById('giftEditMsg').textContent='';
  giftModal.style.display='flex'; document.getElementById('giftFemale').focus();
}

document.getElementById('cancelGiftEdit').addEventListener('click',()=>giftModal.style.display='none');
giftModal.addEventListener('click',e=>{if(e.target===giftModal)giftModal.style.display='none';});

document.getElementById('saveGiftEdit').addEventListener('click',async()=>{
  const cat=document.getElementById('giftCat').value.trim();
  const f=document.getElementById('giftFemale').value.trim();
  const m=document.getElementById('giftMale').value.trim()||f;
  const msg=document.getElementById('giftEditMsg');
  if(!cat){msg.textContent='分類名稱不能空白';return;}
  if(!f){msg.textContent='女性贈品不能空白';return;}
  if(editingGiftCat && editingGiftCat!==cat) delete giftRules[editingGiftCat];
  giftRules[cat]={female:f,male:m};
  await saveGiftRules(); giftModal.style.display='none';
});

async function delGift(cat){
  if(!confirm(`確定刪除「${cat}」的贈品規則？`))return;
  delete giftRules[cat]; await saveGiftRules();
}

async function saveGiftRules(){
  await fetch('/api/dev/gift-rules',{
    method:'POST',headers:{'X-Dev-Token':devToken,'Content-Type':'application/json'},
    body:JSON.stringify(giftRules)
  });
  renderGiftTable();
}

/* ══ 文字匯入贈品 ══ */
const textImportModal=document.getElementById('textImportModal');
document.getElementById('importGiftBtn').addEventListener('click',()=>{
  document.getElementById('giftTextArea').value='';
  document.getElementById('textImportMsg').textContent='';
  textImportModal.style.display='flex';
  document.getElementById('giftTextArea').focus();
});
document.getElementById('cancelTextImport').addEventListener('click',()=>textImportModal.style.display='none');
textImportModal.addEventListener('click',e=>{if(e.target===textImportModal)textImportModal.style.display='none';});
document.getElementById('confirmTextImport').addEventListener('click',async()=>{
  const text=document.getElementById('giftTextArea').value.trim();
  const msg=document.getElementById('textImportMsg');
  if(!text){msg.textContent='請貼上文字';return;}
  const newRules={};
  const lines=text.split('\n').map(l=>l.trim()).filter(l=>l&&!l.startsWith('#'));
  for(const line of lines){
    const parts=line.split('|').map(p=>p.trim());
    if(parts.length<2)continue;
    const [cat,f,m]=parts;
    if(!cat||!f)continue;
    newRules[cat]={female:f,male:m||f};
  }
  if(Object.keys(newRules).length===0){
    msg.textContent='沒有解析到有效規則，格式：分類名稱 | 女性贈品 | 男性贈品';
    msg.className='form-msg err'; return;
  }
  giftRules=newRules; await saveGiftRules();
  textImportModal.style.display='none'; msg.textContent='';
});

/* ══ 修改密碼 ══ */
document.getElementById('savePwdBtn').addEventListener('click',async()=>{
  const cur=document.getElementById('curPwd').value;
  const nw=document.getElementById('newPwd').value;
  const nw2=document.getElementById('newPwd2').value;
  const msg=document.getElementById('pwdMsg'); msg.className='form-msg';
  if(!cur||!nw||!nw2){msg.textContent='請填寫所有欄位';msg.classList.add('err');return;}
  if(nw!==nw2){msg.textContent='兩次密碼不一致';msg.classList.add('err');return;}
  if(nw.length<6){msg.textContent='新密碼至少 6 碼';msg.classList.add('err');return;}
  const res=await fetch('/api/dev/change-password',{
    method:'POST',headers:{'X-Dev-Token':devToken,'Content-Type':'application/json'},
    body:JSON.stringify({current:cur,new:nw})
  });
  if(res.ok){
    devToken=nw; sessionStorage.setItem('devToken',nw);
    msg.textContent='密碼已更新！'; msg.classList.add('ok');
    document.getElementById('curPwd').value='';
    document.getElementById('newPwd').value='';
    document.getElementById('newPwd2').value='';
  } else {
    const err=await res.json(); msg.textContent=err.detail||'更新失敗'; msg.classList.add('err');
  }
});

function escHtml(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
