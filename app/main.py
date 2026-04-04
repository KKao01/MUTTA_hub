"""
Mutta Hub — 母系統後端
port 8002
"""
import os, json, uuid, hashlib, shutil
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR   = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
GALLERY_DIR = BASE_DIR / "uploads" / "gallery"
GALLERY_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "password_hash": "ac9689e2272427085e35b9d3e3e8bed88cb3434828b43b86fc0596cad4c6e270",
    "links": [
        {"label": "MeepShop 後台", "url": "https://meepshop.com", "sub": "meepshop.com"},
        {"label": "順豐寄件",     "url": "https://www.sf-express.com", "sub": "sf-express.com"}
    ],
    "gallery": ["", "", "", "", "", "", "", "", ""],
    "ports": {
        "supermarket": 8000,
        "sf": 8001
    }
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    cfg = DEFAULT_CONFIG.copy()
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
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
app.mount("/static",  StaticFiles(directory=str(BASE_DIR / "static")),  name="static")
app.mount("/gallery", StaticFiles(directory=str(GALLERY_DIR)),           name="gallery")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ── Pages ──────────────────────────────────────────────────────────────────
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/dev")
async def dev_page(request: Request):
    return templates.TemplateResponse(request, "dev.html")

# ── Public API ──────────────────────────────────────────────────────────────
@app.get("/api/config")
async def get_config():
    cfg = load_config()
    return {"links": cfg.get("links", []), "gallery": cfg.get("gallery", []), "ports": cfg.get("ports", {})}

# ── Dev API ─────────────────────────────────────────────────────────────────
@app.post("/api/dev/login")
async def dev_login(password: str = Form(...)):
    cfg = load_config()
    if hash_pw(password) != cfg.get("password_hash", ""):
        raise HTTPException(401, "密碼錯誤")
    return {"ok": True, "token": password}

@app.post("/api/dev/links")
async def update_links(request: Request, _=Depends(require_dev)):
    body = await request.json()
    cfg = load_config()
    cfg["links"] = body
    save_config(cfg)
    return {"ok": True}

@app.post("/api/dev/gallery/{idx}")
async def upload_gallery(idx: int, file: UploadFile = File(...), _=Depends(require_dev)):
    if not 0 <= idx <= 8:
        raise HTTPException(400, "索引超出範圍")
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "只接受圖片")
    ext = Path(file.filename).suffix.lower() or ".jpg"
    fname = f"gallery_{idx}{ext}"
    dest = GALLERY_DIR / fname
    content = await file.read()
    dest.write_bytes(content)
    cfg = load_config()
    while len(cfg["gallery"]) < 9:
        cfg["gallery"].append("")
    cfg["gallery"][idx] = f"/gallery/{fname}"
    save_config(cfg)
    return {"ok": True, "url": f"/gallery/{fname}"}

@app.delete("/api/dev/gallery/{idx}")
async def delete_gallery(idx: int, _=Depends(require_dev)):
    cfg = load_config()
    if 0 <= idx < len(cfg["gallery"]):
        old = cfg["gallery"][idx]
        if old:
            p = BASE_DIR / old.lstrip("/")
            if p.exists():
                p.unlink()
        cfg["gallery"][idx] = ""
        save_config(cfg)
    return {"ok": True}

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
