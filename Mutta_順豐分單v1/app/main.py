from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import os, sys, json, uuid, zipfile
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATE_PATH = BASE_DIR / "sf_template.xlsx"
CONFIG_PATH = BASE_DIR / "config.json"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(BASE_DIR / "app"))
from sf_logic import parse_sf_pdf, generate_sf_pdfs, generate_sf_excel
from core_logic import inject_price_map, inject_gift_rules

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

DEFAULT_CONFIG = {
    "password_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
    "price_map": {},
    "product_map": {},
    "gift_rules": {
        "1+1慕斯":   {"female": "紫撲+C1+F1+乳液各1（盒）",   "male": "黃撲+C1+F1+乳液各1（盒）"},
        "2+2慕斯":   {"female": "紫撲+六款包各1（盒）+卡",     "male": "黃撲+六款包各1（盒）+卡"},
        "紫色慕斯X2": {"female": "紫撲+C1+F1+乳液各1（盒）",   "male": "紫撲+C1+F1+乳液各1（盒）"},
        "黃色慕斯X2": {"female": "黃撲+C1+F1+乳液各1（盒）",   "male": "黃撲+C1+F1+乳液各1（盒）"},
        "紫色慕斯X4": {"female": "紫撲+六款包各1（盒）+卡",     "male": "紫撲+六款包各1（盒）+卡"},
        "黃色慕斯X4": {"female": "黃撲+六款包各1（盒）+卡",     "male": "黃撲+六款包各1（盒）+卡"},
        "白乳X2":    {"female": "刮板+F2+水光2+袋",            "male": "面膜各1+C2+F2（盒）+沐包各2（盒）+卡"},
        "痘乳X2":    {"female": "刮板+C2+痘沐2+袋",            "male": "面膜各1+C2+F2（盒）+沐包各2（盒）+卡"},
        "乳液1+1":   {"female": "刮板+C2+痘沐2（盒）+袋子",    "male": "面膜各1+C2+F2（盒）+沐包各2（盒）+卡"},
        "2+2乳液":   {"female": "刮板+C2+痘沐2（盒）+袋",      "male": "面膜各1+C2+F2（盒）+沐包各2（盒）+卡"},
        "白乳X1":    {"female": "C2+F2（盒）沐包各2（盒）+卡",  "male": "C2+F2（盒）沐包各2（盒）+卡"},
        "痘乳X1":    {"female": "C2+F2（盒）沐包各2（盒）+卡",  "male": "C2+F2（盒）沐包各2（盒）+卡"},
        "晚A+白乳":  {"female": "紫撲+F2+水光2（盒）",         "male": "紫撲+F2+水光2（盒）"},
        "早C+痘乳":  {"female": "黃撲+C2+痘沐2（盒）",         "male": "黃撲+C2+痘沐2（盒）"},
        "痘乳+淨痘沐": {"female": "球+C2+F2（盒）+卡",         "male": "球+C2+F2（盒）+卡"},
        "白乳+水光沐": {"female": "球+C2+F2（盒）+卡",         "male": "球+C2+F2（盒）+卡"},
        "黃慕斯+痘乳": {"female": "黃撲+C2+痘沐2（盒）+卡",   "male": "黃撲+C2+痘沐2（盒）+卡"},
        "紫慕斯+白乳": {"female": "紫撲+F2+水光2（盒）+卡",   "male": "紫撲+F2+水光2（盒）+卡"},
        "所有兩沐":  {"female": "球+C1.F1.乳液各1（盒）+卡",   "male": "球+C1.F1.乳液各1（盒）+卡"},
        "所有一沐":  {"female": "球+C1.F1.乳液各1（盒）+卡",   "male": "球+C1.F1.乳液各1（盒）+卡"},
        "紫+綠+橘":  {"female": "梳+沐包各2+乳液各1（盒）+卡", "male": "梳+沐包各2+乳液各1（盒）+卡"},
        "粉+綠+橘":  {"female": "梳+沐包各2+乳液各1（盒）+卡", "male": "梳+沐包各2+乳液各1（盒）+卡"},
        "紫+綠":     {"female": "梳+海棠管（檢）+卡",           "male": "梳+海棠管（檢）+卡"},
        "紫+橘":     {"female": "梳+沐包各2（盒）+卡",          "male": "梳+沐包各2（盒）+卡"},
        "粉+綠":     {"female": "梳+海棠管（檢）+卡",           "male": "梳+海棠管（檢）+卡"},
        "粉+橘":     {"female": "梳+沐包各2（盒）+卡",          "male": "梳+沐包各2（盒）+卡"},
        "粉洗+紫洗": {"female": "梳+海棠管（檢）+卡",           "male": "梳+海棠管（檢）+卡"},
        "粉洗X2":   {"female": "梳+海棠管（檢）+卡",            "male": "梳+海棠管（檢）+卡"},
        "紫洗X2":   {"female": "梳+海棠管（檢）+卡",            "male": "梳+海棠管（檢）+卡"},
        "粉洗+粉潤": {"female": "梳+海棠管（檢）+卡",           "male": "梳+海棠管（檢）+卡"},
        "紫洗+紫潤": {"female": "梳+海棠管（檢）+卡",           "male": "梳+海棠管（檢）+卡"},
        "小粉洗X1":  {"female": "海棠管+沐包各1+乳液各1（盒）+卡", "male": "海棠管+沐包各1+乳液各1（盒）+卡"},
        "小紫洗X1":  {"female": "海棠管+沐包各1+乳液各1（盒）+卡", "male": "海棠管+沐包各1+乳液各1（盒）+卡"},
        "綠2+橘2精粹": {"female": "梳+C2+F2（盒）+卡",         "male": "梳+C2+F2（盒）+卡"},
        "橘4精粹":   {"female": "梳+C2+F2（盒）+卡",           "male": "梳+C2+F2（盒）+卡"},
        "綠4精粹":   {"female": "梳+C2+F2（盒）+卡",           "male": "梳+C2+F2（盒）+卡"},
        "1+1精粹":   {"female": "梳+C2+F2（盒）+卡",           "male": "梳+C2+F2（盒）+卡"},
        "橘2精粹":   {"female": "梳+C2+F2（盒）+卡",           "male": "梳+C2+F2（盒）+卡"},
        "綠2精粹":   {"female": "梳+C2+F2（盒）+卡",           "male": "梳+C2+F2（盒）+卡"},
        "1小矮":     {"female": "梳+C1+F1（不要盒）+卡",       "male": "梳+C1+F1（不要盒）+卡"},
    }
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except Exception:
            cfg = DEFAULT_CONFIG.copy()
    else:
        cfg = DEFAULT_CONFIG.copy()
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
    inject_price_map(cfg.get('price_map', {}))
    inject_gift_rules(cfg.get('gift_rules', {}))
    return cfg

load_config()

job_store = {}

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/api/process")
async def process(
    pdf_file: UploadFile = File(...),
    csv_file: UploadFile = File(...),
    print_gift: str = Form("true"),
):
    job_id = uuid.uuid4().hex
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir()

    try:
        # 儲存上傳檔案
        pdf_path = str(UPLOAD_DIR / f"{job_id}.pdf")
        csv_path = str(UPLOAD_DIR / f"{job_id}.csv")
        with open(pdf_path, 'wb') as f:
            f.write(await pdf_file.read())
        with open(csv_path, 'wb') as f:
            f.write(await csv_file.read())

        # 解析 CSV
        import pandas as pd
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(csv_path, encoding='utf-8')

        def normalize_phone(val):
            """台灣手機號碼正規化：補回被 CSV/Excel 去掉的開頭 0"""
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return ''
            s = str(val).strip()
            if s in ('', 'nan', 'NaN', 'None'):
                return ''
            try:
                num = str(int(float(s)))   # 處理 975718130 或 975718130.0
            except (ValueError, OverflowError):
                num = s
            if num and not num.startswith('0'):
                num = '0' + num
            return num

        csv_data = {}
        for _, row in df.iterrows():
            oid = str(row.get('廠商訂單編號', '')).strip()
            if not oid or oid == 'nan':
                continue

            # 優先取手機，若空才取電話
            mobile = row.get('收件人手機')
            tel    = row.get('收件人電話')
            if pd.isna(mobile) if isinstance(mobile, float) else (str(mobile).strip() in ('', 'nan')):
                raw_phone = tel
            else:
                raw_phone = mobile

            csv_data[oid] = {
                'name':    str(row.get('收件人姓名', '')).strip(),
                'phone':   normalize_phone(raw_phone),
                'address': str(row.get('收件人地址', '')).strip(),
            }

        # 解析 PDF
        load_config()
        orders = parse_sf_pdf(pdf_path, csv_data)
        if not orders:
            raise HTTPException(400, "無法解析訂單，請確認是宅配 PDF 格式")

        # 統計
        from collections import defaultdict
        groups = defaultdict(list)
        for o in orders:
            groups[o['cat']].append(o)

        # 產生分類 PDF
        pg = print_gift.lower() == 'true'
        generate_sf_pdfs(orders, pdf_path, str(job_dir), print_gift=pg)

        # 產生順豐 Excel
        date_str = datetime.now().strftime('%Y%m%d')
        excel_name = f"{date_str}順豐.xlsx"
        excel_path = str(job_dir / excel_name)
        generate_sf_excel(orders, str(TEMPLATE_PATH), excel_path)

        # 統計結果
        stats = []
        total_pages = 0
        for cat in sorted(groups.keys(), key=lambda c: (c == '特殊單', c)):
            ords = groups[cat]
            page_count = sum(len(o['page_indices']) for o in ords)
            total_pages += page_count
            first_gift = ords[0]['gift'].replace('\n', ' ') if ords[0]['gift'] else ''
            stats.append({
                'cat': cat,
                'count': len(ords),
                'pages': page_count,
                'gift_preview': first_gift,
                'is_special': cat == '特殊單',
            })

        job_store[job_id] = {
            'status': 'done',
            'total': len(orders),
            'total_pages': total_pages,
            'cat_count': len(groups),
            'stats': stats,
            'excel_name': excel_name,
        }
        return {'job_id': job_id, **job_store[job_id]}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(500, f"處理失敗：{e}\n{traceback.format_exc()}")


@app.get("/api/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    path = OUTPUT_DIR / job_id / filename
    if not path.exists():
        raise HTTPException(404, "檔案不存在")
    mt = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          if filename.endswith('.xlsx') else "application/pdf")
    return FileResponse(str(path), filename=filename, media_type=mt)


@app.get("/api/download-all/{job_id}")
async def download_all(job_id: str):
    job_dir = OUTPUT_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(404)
    zip_path = OUTPUT_DIR / f"{job_id}.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for f in job_dir.iterdir():
            zf.write(f, f.name)
    return FileResponse(str(zip_path), filename="順豐分單結果.zip",
                        media_type="application/zip")
