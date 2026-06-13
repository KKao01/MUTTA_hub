"""
Mutta Hub — 母系統後端
"""
import os, json, hashlib
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR    = Path(__file__).parent.parent
STATIC_DIR  = BASE_DIR / "static"
# 持久化資料夾：在 Railway 掛一個 Volume 後，設環境變數 DATA_DIR=/data 指向它。
# 沒設 DATA_DIR 時退回 repo 根目錄（本機開發照舊）。
DATA_DIR    = Path(os.environ.get("DATA_DIR", str(BASE_DIR)))
MEDIA_DIR   = DATA_DIR / "media"
CONFIG_PATH = DATA_DIR / "config.json"
REPO_CONFIG = BASE_DIR / "config.json"   # 隨程式打包的種子設定（保留已 commit 的密碼/版面）
MAX_BG_MB   = 20

DATA_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "password_hash": "ac9689e2272427085e35b9d3e3e8bed88cb3434828b43b86fc0596cad4c6e270",
    "background": {"type": "video", "video": "/static/bg.mp4", "darken": 50},
    "cards": [
        {"id": "route", "r": 1, "c": 1, "visible": True, "icon": "⊟", "title": "分單系統", "sub": "Order Routing",   "tag1": "超商", "tag2": "順豐", "accent": "#36b37e", "href": "https://mutta-v-40-production.up.railway.app/"},
        {"id": "track", "r": 1, "c": 2, "visible": True, "icon": "◎", "title": "貨態查詢", "sub": "Tracking System", "tag1": "超商", "tag2": "順豐", "accent": "#B87333", "href": "https://mutta-track-production.up.railway.app/admin"},
        {"id": "cs",    "r": 2, "c": 1, "visible": True, "icon": "✦", "title": "客服助理", "sub": "CS Assistant",     "tag1": "AI 輔助", "tag2": "", "accent": "#C8A96E", "href": "https://muttacs-production.up.railway.app"},
        {"id": "line",  "r": 2, "c": 2, "visible": True, "icon": "◍", "title": "LINE Bot", "sub": "Chat Bot Admin",  "tag1": "LINE", "tag2": "CMS", "accent": "#06C755", "href": "https://line-bot-production-cb18.up.railway.app/"},
        {"id": "gift",  "r": 3, "c": 1, "visible": True, "icon": "⊕", "title": "贈品設定", "sub": "Gift Builder",     "tag1": "滿額贈", "tag2": "GTM", "accent": "#c9a896", "href": "https://muttagiftbuilder-production.up.railway.app/"}
    ],
    "bars": [
        {"id": "b1", "col": 1, "title": "MeepShop 後台", "href": "https://admin.meepshop.tw/", "accent": "#8fb6ff"},
        {"id": "b2", "col": 2, "title": "順豐寄件",       "href": "https://www.sf-express.com", "accent": "#8fb6ff"}
    ],
    "texts": [
        {"id": "t1", "t": "KKAO x Mutta", "x": 50, "y": 28, "size": 30, "w": 700, "a": "center", "c": None, "tone": "mid", "bg": "none"}
    ]
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception:
            pass
    # 第一次：優先用 repo 內已 commit 的 config.json 當種子（保留密碼/版面），否則用預設
    seed = None
    if REPO_CONFIG.exists() and REPO_CONFIG.resolve() != CONFIG_PATH.resolve():
        try:
            seed = json.loads(REPO_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            seed = None
    cfg = seed if seed else json.loads(json.dumps(DEFAULT_CONFIG))
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    save_config(cfg)
    return cfg

def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def require_dev(request: Request):
    token = request.headers.get("X-Dev-Token", "")
    cfg = load_config()
    if not token or hash_pw(token) != cfg.get("password_hash", ""):
        raise HTTPException(401, "未授權")

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ── Pages ──
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/dev")
async def dev_page(request: Request):
    return templates.TemplateResponse(request, "dev.html")

# ── Public API ──
@app.get("/api/config")
async def get_config():
    cfg = load_config()
    return {
        "background": cfg.get("background", DEFAULT_CONFIG["background"]),
        "cards": cfg.get("cards", []),
        "bars": cfg.get("bars", []),
        "texts": cfg.get("texts", []),
    }

# ── Dev API ──
@app.post("/api/dev/login")
async def dev_login(password: str = Form(...)):
    cfg = load_config()
    if hash_pw(password) != cfg.get("password_hash", ""):
        raise HTTPException(401, "密碼錯誤")
    return {"ok": True, "token": password}

def _sanitize_layout(cards, bars, texts):
    clean_cards = []
    for k in (cards or [])[:21]:
        clean_cards.append({
            "id": str(k.get("id", ""))[:40] or os.urandom(3).hex(),
            "r": max(1, min(3, int(k.get("r", 1)))),
            "c": max(1, min(7, int(k.get("c", 1)))),
            "visible": bool(k.get("visible", True)),
            "icon": str(k.get("icon", ""))[:4],
            "title": str(k.get("title", ""))[:40],
            "sub": str(k.get("sub", ""))[:60],
            "tag1": str(k.get("tag1", ""))[:20],
            "tag2": str(k.get("tag2", ""))[:20],
            "accent": str(k.get("accent", "#8fb6ff"))[:9],
            "href": str(k.get("href", ""))[:500],
        })
    clean_bars = []
    for b in (bars or [])[:5]:
        clean_bars.append({
            "id": str(b.get("id", ""))[:40] or os.urandom(3).hex(),
            "col": max(1, min(5, int(b.get("col", 1)))),
            "title": str(b.get("title", ""))[:40],
            "href": str(b.get("href", ""))[:500],
            "accent": str(b.get("accent", "#8fb6ff"))[:9],
        })
    clean_texts = []
    for t in (texts or [])[:20]:
        c = t.get("c")
        clean_texts.append({
            "id": str(t.get("id", ""))[:40] or os.urandom(3).hex(),
            "t": str(t.get("t", ""))[:200],
            "x": max(0.0, min(100.0, float(t.get("x", 50)))),
            "y": max(0.0, min(100.0, float(t.get("y", 50)))),
            "size": max(8, min(200, int(t.get("size", 22)))),
            "w": 700 if int(t.get("w", 400)) >= 700 else 400,
            "a": t.get("a") if t.get("a") in ("left", "center", "right") else "center",
            "c": (str(c)[:9] if c else None),
            "tone": t.get("tone") if t.get("tone") in ("strong", "mid", "soft") else "mid",
            "bg": t.get("bg") if t.get("bg") in ("none", "glass", "white") else "none",
        })
    return clean_cards, clean_bars, clean_texts

@app.post("/api/dev/layout")
async def save_layout(request: Request, _=Depends(require_dev)):
    body = await request.json()
    cards, bars, texts = _sanitize_layout(body.get("cards"), body.get("bars"), body.get("texts"))
    cfg = load_config()
    cfg["cards"] = cards
    cfg["bars"] = bars
    cfg["texts"] = texts
    save_config(cfg)
    return {"ok": True, "cards": len(cards), "bars": len(bars), "texts": len(texts)}

@app.post("/api/dev/background")
async def set_background(request: Request, _=Depends(require_dev)):
    body = await request.json()
    btype = body.get("type", "video")
    if btype not in ("video", "shader", "none"):
        raise HTTPException(400, "背景類型錯誤")
    try:
        darken = int(body.get("darken", 50))
    except Exception:
        darken = 50
    darken = max(0, min(80, darken))
    cfg = load_config()
    bg = cfg.get("background", {}) or {}
    bg["type"] = btype
    bg["darken"] = darken
    bg.setdefault("video", "/static/bg.mp4")
    cfg["background"] = bg
    save_config(cfg)
    return {"ok": True, "background": bg}

@app.post("/api/dev/background/video")
async def upload_background_video(request: Request, file: UploadFile = File(...), _=Depends(require_dev)):
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(400, "只接受影片檔")
    limit = MAX_BG_MB * 1024 * 1024
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > limit:
        raise HTTPException(413, f"影片太大（約 {int(cl)//1048576} MB）。請先壓到 {MAX_BG_MB} MB 以下再上傳。")
    size, chunks = 0, []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, f"影片太大。請先用本機工具壓到 {MAX_BG_MB} MB 以下再上傳。")
        chunks.append(chunk)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "bg.mp4").write_bytes(b"".join(chunks))
    cfg = load_config()
    bg = cfg.get("background", {}) or {}
    bg["type"] = "video"; bg["video"] = "/media/bg.mp4"; bg.setdefault("darken", 50)
    cfg["background"] = bg
    save_config(cfg)
    return {"ok": True, "url": "/media/bg.mp4", "size": size}

@app.post("/api/dev/change-password")
async def change_password(request: Request, _=Depends(require_dev)):
    body = await request.json()
    new_pw = body.get("new", "").strip()
    if len(new_pw) < 6:
        raise HTTPException(400, "密碼至少 6 碼")
    cfg = load_config()
    cfg["password_hash"] = hash_pw(new_pw)
    save_config(cfg)
    return {"ok": True}
