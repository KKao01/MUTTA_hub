"""
分單系統 Web 版 — FastAPI 後端
"""
import os, re, json, uuid, shutil, hashlib, asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR  = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
CONFIG_FILE = BASE_DIR / "config.json"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 設定管理 ──────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "dev_password_hash": hashlib.sha256(b"admin1234").hexdigest(),
    "price_map": {
        "880":  {"kind": "1小矮"},
        "1350": {"kind": "洗+精粹"},
        "1360": {"kind": "洗潤"},
        "1370": {"kind": "兩沐"},
        "1395": {"kind": "乳+慕斯"},
        "1520": {"kind": "精粹2"},
        "1576": {"kind": "乳+沐"},
        "785":  {"kind": "一沐"},
        "780":  {"kind": "一洗潤"},
        "950":  {"kind": "乳X1"},
        "689":  {"kind": "慕斯X1"},
        "1248": {"kind": "慕斯1+1"},
        "1860": {"kind": "乳X2"},
        "2184": {"kind": "慕斯2+2"},
        "2850": {"kind": "精粹4"},
        "2420": {"kind": "沐X4"},
        "2380": {"kind": "洗X4"},
        "1688": {"kind": "特殊"},
        "1080": {"kind": "乳X1特殊"},
        "1060": {"kind": "乳X1特殊"}
    },
    "gift_rules": {
        "1+1慕斯":     {"female": "紫撲+C1+F1+乳液各1（盒）", "male": "黃撲+C1+F1+乳液各1（盒）"},
        "2+2慕斯":     {"female": "紫撲+六款包各1（盒）+卡",  "male": "黃撲+六款包各1（盒）+卡"},
        "早C+痘乳":    {"female": "黃撲+C2+痘沐2（盒）",      "male": "黃撲+C2+痘沐2（盒）"},
        "晚A+白乳":    {"female": "紫撲+F2+水光2（盒）",      "male": "紫撲+F2+水光2（盒）"},
        "黃色慕斯X2":  {"female": "黃撲+C1+F1+乳液各1（盒）", "male": "黃撲+C1+F1+乳液各1（盒）"},
        "黃色慕斯X4":  {"female": "黃撲+六款包各1（盒）+卡",  "male": "黃撲+六款包各1（盒）+卡"},
        "紫色慕斯X2":  {"female": "紫撲+C1+F1+乳液各1（盒）", "male": "紫撲+C1+F1+乳液各1（盒）"},
        "紫色慕斯X4":  {"female": "紫撲+六款包各1（盒）+卡",  "male": "紫撲+六款包各1（盒）+卡"},
        "白乳X2":      {"female": "刮板+F2+水光2+袋",         "male": "面膜各1+C2+F2（盒）+沐包各2（盒）+卡"},
        "痘乳X2":      {"female": "刮板+C2+痘沐2+袋",         "male": "面膜各1+C2+F2（盒）+沐包各2（盒）+卡"},
        "白乳X1":      {"female": "C2+F2（盒）+沐包各2（盒）+卡", "male": "C2+F2（盒）+沐包各2（盒）+卡"},
        "痘乳X1":      {"female": "C2+F2（盒）+沐包各2（盒）+卡", "male": "C2+F2（盒）+沐包各2（盒）+卡"},
        "乳液1+1":     {"female": "刮板+C2+痘沐2（盒）+袋子", "male": "面膜各1+C2+F2（盒）+沐包各2（盒）+卡"},
        "2+2乳液":     {"female": "刮板+C2+痘沐2（盒）+袋",   "male": "面膜各1+C2+F2（盒）+沐包各2（盒）+卡"},
        "痘乳+淨痘沐": {"female": "球+C2+F2（盒）+卡",        "male": "球+C2+F2（盒）+卡"},
        "白乳+水光沐": {"female": "球+C2+F2（盒）+卡",        "male": "球+C2+F2（盒）+卡"},
        "兩沐":        {"female": "球+C1.F1.乳液各1（盒）+卡","male": "球+C1.F1.乳液各1（盒）+卡"},
        "一沐":        {"female": "球+C1.F1.乳液各1（盒）+卡","male": "球+C1.F1.乳液各1（盒）+卡"},
        "綠2+橘2精粹": {"female": "梳+C2+F2（盒）+卡",        "male": "梳+C2+F2（盒）+卡"},
        "橘4精粹":     {"female": "梳+C2+F2（盒）+卡",        "male": "梳+C2+F2（盒）+卡"},
        "綠4精粹":     {"female": "梳+C2+F2（盒）+卡",        "male": "梳+C2+F2（盒）+卡"},
        "橘2精粹":     {"female": "梳+C2+F2（盒）+卡",        "male": "梳+C2+F2（盒）+卡"},
        "綠2精粹":     {"female": "梳+C2+F2（盒）+卡",        "male": "梳+C2+F2（盒）+卡"},
        "1+1精粹":     {"female": "梳+C2+F2（盒）+卡",        "male": "梳+C2+F2（盒）+卡"},
        "1小矮":       {"female": "梳+C1+F1（不要盒）+卡",    "male": "梳+C1+F1（不要盒）+卡"},
        "粉+綠+橘":    {"female": "梳+沐包各2+乳液各1（盒）+卡","male": "梳+沐包各2+乳液各1（盒）+卡"},
        "粉+橘":       {"female": "梳+沐包各2（盒）+卡",      "male": "梳+沐包各2（盒）+卡"},
        "粉+綠":       {"female": "梳+海棠管（檢）+卡",       "male": "梳+海棠管（檢）+卡"},
        "紫+綠+橘":    {"female": "梳+沐包各2+乳液各1（盒）+卡","male": "梳+沐包各2+乳液各1（盒）+卡"},
        "紫+橘":       {"female": "梳+沐包各2（盒）+卡",      "male": "梳+沐包各2（盒）+卡"},
        "紫+綠":       {"female": "梳+海棠管（檢）+卡",       "male": "梳+海棠管（檢）+卡"},
        "粉洗+紫洗":   {"female": "梳+海棠管（檢）+卡",       "male": "梳+海棠管（檢）+卡"},
        "粉洗X2":      {"female": "梳+海棠管（檢）+卡",       "male": "梳+海棠管（檢）+卡"},
        "紫洗X2":      {"female": "梳+海棠管（檢）+卡",       "male": "梳+海棠管（檢）+卡"},
        "粉洗+粉潤":   {"female": "梳+海棠管（檢）+卡",       "male": "梳+海棠管（檢）+卡"},
        "紫洗+紫潤":   {"female": "梳+海棠管（檢）+卡",       "male": "梳+海棠管（檢）+卡"},
        "小粉洗X1":    {"female": "海棠管+沐包各1+乳液各1（盒）+卡","male": "海棠管+沐包各1+乳液各1（盒）+卡"},
        "小紫洗X1":    {"female": "海棠管+沐包各1+乳液各1（盒）+卡","male": "海棠管+沐包各1+乳液各1（盒）+卡"}
    }
}

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def verify_dev_password(password: str) -> bool:
    cfg = load_config()
    return hashlib.sha256(password.encode()).hexdigest() == cfg.get("dev_password_hash", "")

# ── 任務狀態（記憶體，簡單版） ────────────────────────────────────────────────
job_store: dict[str, dict] = {}

# ── 內建自動對照表（商品名稱|||品項 → 分類名稱）────────────────────────────────
AUTO_PRODUCT_MAP = {
    # 慕斯系列
    "【醫美院線級別Ｘ煥膚黑科技】限時7折！早Ｃ晚Ａ超進化！超導繃繃煥膚ALL IN ONE雲朵面膜！（多規格可選）|||早Ｃ活氧瓶Ｘ1＋晚Ａ凍齡瓶Ｘ1": "1+1慕斯",
    "【醫美院線級別Ｘ煥膚黑科技】限時7折！早Ｃ晚Ａ超進化！超導繃繃煥膚ALL IN ONE雲朵面膜！（多規格可選）|||早Ｃ活氧瓶Ｘ2＋晚Ａ凍齡瓶Ｘ2": "2+2慕斯",
    "【醫美院線級別Ｘ煥膚黑科技】限時7折！早Ｃ晚Ａ超進化！超導繃繃煥膚ALL IN ONE雲朵面膜！（多規格可選）|||早Ｃ活氧瓶Ｘ4": "黃色慕斯X4",
    "【醫美院線級別Ｘ煥膚黑科技】限時7折！早Ｃ晚Ａ超進化！超導繃繃煥膚ALL IN ONE雲朵面膜！（多規格可選）|||晚Ａ凍齡瓶Ｘ4": "紫色慕斯X4",
    "【醫美院線級別Ｘ煥膚黑科技】超導維Ｃ＋24K抗氧奈米黃金胜肽！早Ｃ晚Ａ超進化！ALL IN ONE 活氧雲朵面膜|||早Ｃ抗痘活氧瓶Ｘ1": "特殊單",
    "【醫美院線級別Ｘ煥膚黑科技】超導維Ｃ＋24K抗氧奈米黃金胜肽！早Ｃ晚Ａ超進化！ALL IN ONE 活氧雲朵面膜|||早Ｃ抗痘活氧瓶Ｘ2": "黃色慕斯X2",
    "【醫美院線級別Ｘ煥膚黑科技】超導維Ｃ＋24K抗氧奈米黃金胜肽！早Ｃ晚Ａ超進化！ALL IN ONE 活氧雲朵面膜|||早Ｃ抗痘＋晚Ａ緊緻": "1+1慕斯",
    "【醫美院線級別Ｘ煥膚黑科技】超凍齡A醇＋專利PTC緊顏時光胜肽！早Ｃ晚Ａ再進化！ALL IN ONE 抗老雲朵面膜|||晚Ａ凍齡瓶Ｘ1": "特殊單",
    "【醫美院線級別Ｘ煥膚黑科技】超凍齡A醇＋專利PTC緊顏時光胜肽！早Ｃ晚Ａ再進化！ALL IN ONE 抗老雲朵面膜|||晚Ａ凍齡瓶Ｘ2": "紫色慕斯X2",
    "【醫美院線級別Ｘ煥膚黑科技】超凍齡A醇＋專利PTC緊顏時光胜肽！早Ｃ晚Ａ再進化！ALL IN ONE 抗老雲朵面膜|||早Ｃ抗痘＋晚Ａ緊緻": "1+1慕斯",
    # 乳液系列
    "【痘痘橡皮擦Ｘ2000億奢華外泌體】2％水楊酸＋0.1%繖花醇 抗痘拋光身體乳|||抗痘拋光身體乳Ｘ1": "痘乳X1",
    "【痘痘橡皮擦Ｘ2000億奢華外泌體】2％水楊酸＋0.1%繖花醇 抗痘拋光身體乳|||抗痘拋光身體乳Ｘ2": "痘乳X2",
    "【痘痘橡皮擦Ｘ2000億奢華外泌體】2％水楊酸＋0.1%繖花醇 抗痘拋光身體乳|||抗痘拋光乳＋冰河煥白乳": "乳液1+1",
    "【肌膚閃光彈Ｘ2000億奢華外泌體】2％傳明酸＋20%菸鹼醯胺 冰河煥白身體乳|||冰河煥白身體乳Ｘ1": "白乳X1",
    "【肌膚閃光彈Ｘ2000億奢華外泌體】2％傳明酸＋20%菸鹼醯胺 冰河煥白身體乳|||冰河煥白身體乳Ｘ2": "白乳X2",
    "【肌膚閃光彈Ｘ2000億奢華外泌體】2％傳明酸＋20%菸鹼醯胺 冰河煥白身體乳|||冰河煥白乳＋抗痘拋光乳": "乳液1+1",
    # 早C+痘乳 / 晚A+白乳
    "【TOP！爆改韓女媽生皮】早Ｃ活氧瓶＋抗痘拋光乳 極效抗痘組合 限時75折！|||早Ｃ抗痘活氧瓶＋水楊酸拋光身體乳": "早C+痘乳",
    "【TOP！緊顏新生亮膚組】晚Ａ凍齡瓶＋冰河煥白乳 童顏王牌組合 限時75折！|||晚A凍齡瓶+冰河煥白乳": "晚A+白乳",
    # 乳+沐
    "【美肌磨皮術】一鍵開啟燈泡肌！拋光抗痘身體乳＋淨痘舒敏沐浴露|||抗痘拋光身體乳＋淨痘舒敏沐浴露": "痘乳+淨痘沐",
    "【我要超激白】白成人間反光板！冰河煥白身體乳＋水光嫩白沐浴露|||水光嫩白沐浴露＋冰河煥白身體乳": "白乳+水光沐",
    # 沐浴系列
    "【痘肌救星】全能有機系列 淨痘舒敏沐浴露|||淨痘舒敏沐Ｘ1": "一沐",
    "【痘肌救星】全能有機系列 淨痘舒敏沐浴露|||淨痘舒敏沐Ｘ2": "兩沐",
    "【痘肌救星】全能有機系列 淨痘舒敏沐浴露|||淨痘舒敏沐＋水光嫩白沐": "兩沐",
    "【白到發光】全能有機系列 水光嫩白沐浴露|||水光嫩白沐Ｘ1": "一沐",
    "【白到發光】全能有機系列 水光嫩白沐浴露|||水光嫩白沐Ｘ2": "兩沐",
    "【白到發光】全能有機系列 水光嫩白沐浴露|||水光嫩白沐＋淨痘舒敏沐": "兩沐",
    "【膚況開外掛】限時68折！醫美院線級別！歐盟雙認證！全能有機沐浴露 限量超值團購組 （多規格可選）|||淨痘沐浴露Ｘ1＋水光沐浴露Ｘ1": "兩沐",
    "【膚況開外掛】限時68折！醫美院線級別！歐盟雙認證！全能有機沐浴露 限量超值團購組 （多規格可選）|||淨痘沐浴露Ｘ2＋水光沐浴露Ｘ2": "特殊單",
    "【膚況開外掛】限時68折！醫美院線級別！歐盟雙認證！全能有機沐浴露 限量超值團購組 （多規格可選）|||淨痘沐浴露Ｘ4": "特殊單",
    "【膚況開外掛】限時68折！醫美院線級別！歐盟雙認證！全能有機沐浴露 限量超值團購組 （多規格可選）|||水光沐浴露Ｘ4": "特殊單",
    # 精粹系列
    "【炸毛必備】夜間小橘 逆齡重生蘊髮精粹|||夜間小橘瓶Ｘ1": "1小矮",
    "【炸毛必備】夜間小橘 逆齡重生蘊髮精粹|||夜間小橘瓶Ｘ2": "橘2精粹",
    "【炸毛必備】夜間小橘 逆齡重生蘊髮精粹|||夜間小橘瓶＋日用小綠瓶": "1+1精粹",
    "【髮力全開】夜間小橘 逆齡重生蘊髮精粹 限時8折|||逆齡小橘瓶Ｘ2": "橘2精粹",
    "【髮力全開】夜間小橘 逆齡重生蘊髮精粹 限時8折|||日用小綠Ｘ1＋夜用小橘Ｘ1": "1+1精粹",
    "【髮縫加密】日用小綠 奇蹟煥活蘊髮精粹|||日用小綠瓶Ｘ１": "1小矮",
    "【髮縫加密】日用小綠 奇蹟煥活蘊髮精粹|||日用小綠瓶Ｘ2": "綠2精粹",
    "【髮縫加密】日用小綠 奇蹟煥活蘊髮精粹|||日用小綠瓶＋夜間小橘瓶": "1+1精粹",
    "【髮力全開】日用小綠 奇蹟煥活蘊髮精粹 限時8折|||奇蹟小綠瓶Ｘ2": "綠2精粹",
    "【髮力全開】日用小綠 奇蹟煥活蘊髮精粹 限時8折|||日用小綠Ｘ1＋夜用小橘Ｘ1": "1+1精粹",
    "【炸毛永動機】日夜活化不間斷 無限爆髮組 限時75折！2+2 團購組 超能蘊髮日夜雙精粹|||奇蹟小綠瓶Ｘ4": "綠4精粹",
    "【炸毛永動機】日夜活化不間斷 無限爆髮組 限時75折！2+2 團購組 超能蘊髮日夜雙精粹|||逆齡小橘瓶Ｘ4": "橘4精粹",
    "【炸毛永動機】日夜活化不間斷 無限爆髮組 限時75折！2+2 團購組 超能蘊髮日夜雙精粹|||奇蹟小綠瓶Ｘ2＋逆齡小橘瓶Ｘ2": "綠2+橘2精粹",
    # 精粹+洗髮
    "【髮力無邊】豐盈小紫+超能蘊髮精粹 1+1 限時75折 超值入門體驗組！(多規格可選)|||豐盈小紫瓶＋奇蹟小綠瓶": "紫+綠",
    "【髮力無邊】豐盈小紫+超能蘊髮精粹 1+1 限時75折 超值入門體驗組！(多規格可選)|||豐盈小紫瓶＋逆齡小橘瓶": "紫+橘",
    "【髮力無邊】爆毛小粉+超能蘊髮精粹 1+1 限時75折 超值入門體驗組！(多規格可選)|||爆毛小粉洗＋奇蹟小綠瓶": "粉+綠",
    "【髮力無邊】爆毛小粉+超能蘊髮精粹 1+1 限時75折 超值入門體驗組！(多規格可選)|||爆毛小粉洗＋逆齡小橘瓶": "粉+橘",
    # 洗髮單品
    "【髮力全開】爆毛小粉瓶 蓬鬆控油洗髮精|||爆毛小粉洗Ｘ1": "小粉洗X1",
    "【髮力全開】爆毛小粉瓶 蓬鬆控油洗髮精|||爆毛小粉洗Ｘ2": "粉洗X2",
    "【髮力全開】爆毛小粉瓶 蓬鬆控油洗髮精|||爆毛小粉洗＋草本平衡潤": "粉洗+粉潤",
    "【髮力全開】豐盈小紫瓶 強韌修護洗髮精|||豐盈小紫洗Ｘ1": "小紫洗X1",
    "【髮力全開】豐盈小紫瓶 強韌修護洗髮精|||豐盈小紫洗Ｘ2": "紫洗X2",
    "【髮力全開】豐盈小紫瓶 強韌修護洗髮精|||豐盈小紫洗＋亮澤護髮乳": "紫洗+紫潤",
    "【髮力全開】小紫系列 極潤亮澤抗斷護髮乳|||豐盈小紫洗＋亮澤護髮乳": "紫洗+紫潤",
    "【髮力全開】小粉系列 草本平衡輕盈護髮乳|||小粉洗髮精＋草本護髮乳": "粉洗+粉潤",
    "【髮根發電機】爆毛小粉＋豐盈小紫 洗髮混搭超值組 最低7折！|||爆毛小粉洗Ｘ1＋豐盈小紫洗Ｘ1": "粉洗+紫洗",
    "【髮根發電機】爆毛小粉＋豐盈小紫 洗髮混搭超值組 最低7折！|||爆毛小粉洗Ｘ2＋豐盈小紫洗Ｘ2": "特殊單",
    # 1+1洗潤自由配
    "【髮力全開】爆毛小粉系列 1+1洗潤自由配 只要8折|||爆毛小粉洗髮精 / 爆毛小粉洗髮精": "粉洗X2",
    "【髮力全開】爆毛小粉系列 1+1洗潤自由配 只要8折|||爆毛小粉洗髮精 / 草本平衡潤髮乳": "粉洗+粉潤",
    "【髮力全開】爆毛小粉系列 1+1洗潤自由配 只要8折|||草本平衡潤髮乳 / 爆毛小粉洗髮精": "粉洗+粉潤",
    "【髮力全開】爆毛小粉系列 1+1洗潤自由配 只要8折|||草本平衡潤髮乳 / 草本平衡潤髮乳": "特殊單",
    "【髮力全開】豐盈小紫系列 1+1洗潤自由配 只要8折|||豐盈小紫洗髮精 / 豐盈小紫洗髮精": "紫洗X2",
    "【髮力全開】豐盈小紫系列 1+1洗潤自由配 只要8折|||豐盈小紫洗髮精 / 極潤亮澤潤髮乳": "紫洗+紫潤",
    "【髮力全開】豐盈小紫系列 1+1洗潤自由配 只要8折|||極潤亮澤潤髮乳 / 豐盈小紫洗髮精": "紫洗+紫潤",
    "【髮力全開】豐盈小紫系列 1+1洗潤自由配 只要8折|||極潤亮澤潤髮乳 / 極潤亮澤潤髮乳": "特殊單",
    # 護髮乳單品 → 特殊單
    "【髮力全開】小粉系列 草本平衡輕盈護髮乳|||草本護髮乳Ｘ1": "特殊單",
    "【髮力全開】小粉系列 草本平衡輕盈護髮乳|||草本護髮乳Ｘ2": "特殊單",
    "【髮力全開】小紫系列 極潤亮澤抗斷護髮乳|||亮澤護髮乳Ｘ1": "特殊單",
    "【髮力全開】小紫系列 極潤亮澤抗斷護髮乳|||亮澤護髮乳Ｘ2": "特殊單",
}

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="分單系統", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ── 頁面路由 ──────────────────────────────────────────────────────────────────
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/dev")
async def dev_page(request: Request):
    return templates.TemplateResponse(request, "dev.html")

# ── API：上傳 PDF（支援多檔，自動合併） ────────────────────────────────────
@app.post("/api/upload")
async def upload_pdf(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "請上傳至少一個 PDF 檔案")
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(400, f"只接受 PDF 檔案：{f.filename}")

    job_id = uuid.uuid4().hex
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir()
    dest = job_dir / "input.pdf"

    if len(files) == 1:
        dest.write_bytes(await files[0].read())
        display_name = files[0].filename
    else:
        # 多檔合併
        from pypdf import PdfWriter
        writer = PdfWriter()
        for f in files:
            from pypdf import PdfReader
            from io import BytesIO
            content = await f.read()
            reader = PdfReader(BytesIO(content))
            for page in reader.pages:
                writer.add_page(page)
        with open(dest, 'wb') as out:
            writer.write(out)
        display_name = f"{files[0].filename} 等 {len(files)} 個檔案"

    job_store[job_id] = {"status": "uploaded", "filename": display_name, "logs": []}
    return {"job_id": job_id, "filename": display_name}

# ── API：執行分單 ─────────────────────────────────────────────────────────────
@app.post("/api/process/{job_id}")
async def process_pdf(job_id: str, print_gift: bool = Form(True)):
    if job_id not in job_store:
        raise HTTPException(404, "找不到此任務")
    job = job_store[job_id]
    if job["status"] == "running":
        raise HTTPException(409, "任務進行中")

    job["status"] = "running"
    job["logs"] = []
    job["progress"] = 0
    asyncio.create_task(_run_job(job_id, print_gift))
    return {"ok": True}

async def _run_job(job_id: str, print_gift: bool):
    job = job_store[job_id]
    def log(msg: str, tag: str = ""):
        ts = datetime.now().strftime("%H:%M:%S")
        job["logs"].append({"ts": ts, "msg": msg, "tag": tag})

    try:
        pdf_in = str(UPLOAD_DIR / job_id / "input.pdf")
        out_dir = str(OUTPUT_DIR / job_id)
        os.makedirs(out_dir, exist_ok=True)

        log(f"載入 PDF：{job['filename']}")
        job["progress"] = 5

        import sys
        sys.path.insert(0, str(BASE_DIR / "app"))
        import core_logic as cl

        cfg = load_config()
        cl.inject_price_map(cfg.get("price_map", {}))
        cl.inject_gift_rules(cfg.get("gift_rules", {}))

        await asyncio.sleep(0.1)
        log("解析訂單編號與收件人...")
        job["progress"] = 15

        loop = asyncio.get_event_loop()
        orders = await loop.run_in_executor(None, cl.parse_pdf, pdf_in)
        job["progress"] = 55
        log(f"共識別 {len(orders)} 筆訂單", "ok")

        log("依分類分組並輸出 PDF...")
        job["progress"] = 70
        output_files = await loop.run_in_executor(
            None, cl.generate_pdfs, orders, pdf_in, out_dir, print_gift
        )
        job["progress"] = 100

        from collections import defaultdict
        groups = defaultdict(list)
        for o in orders:
            groups[o["cat"]].append(o)

        results = []
        for path in output_files:
            basename = os.path.splitext(os.path.basename(path))[0]
            # 去掉數字前綴（例如 "01_1+1慕斯" → "1+1慕斯"）
            cat = re.sub(r'^\d+_', '', basename)
            cat_orders = groups.get(cat, [])
            pages = sum(len(o.get("page_indices", [0])) for o in cat_orders)
            gift_sample = cat_orders[0]["gift"] if cat_orders else ""
            is_special = cat_orders[0].get("special", False) if cat_orders else False
            results.append({
                "cat": cat,
                "filename": os.path.basename(path),
                "count": len(cat_orders),
                "pages": pages,
                "gift": gift_sample,
                "special": is_special,
                "url": f"/api/download/{job_id}/{os.path.basename(path)}"
            })
            log(f"[{cat}]  {len(cat_orders)} 筆  {pages} 頁", "warn" if is_special else "ok")

        job["status"] = "done"
        job["results"] = results
        log(f"完成！共 {len(output_files)} 個分類 PDF", "ok")

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        log(f"錯誤：{e}", "err")

# ── API：查詢進度 ─────────────────────────────────────────────────────────────
@app.get("/api/status/{job_id}")
async def job_status(job_id: str):
    if job_id not in job_store:
        raise HTTPException(404, "找不到此任務")
    return job_store[job_id]

# ── API：下載單一 PDF ─────────────────────────────────────────────────────────
@app.get("/api/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    path = OUTPUT_DIR / job_id / filename
    if not path.exists():
        raise HTTPException(404, "檔案不存在")
    return FileResponse(str(path), filename=filename,
                        media_type="application/pdf")

# ── API：打包下載全部 ─────────────────────────────────────────────────────────
@app.get("/api/download-all/{job_id}")
async def download_all(job_id: str):
    out_dir = OUTPUT_DIR / job_id
    if not out_dir.exists():
        raise HTTPException(404)
    zip_path = OUTPUT_DIR / f"{job_id}.zip"
    import zipfile
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in out_dir.glob("*.pdf"):
            zf.write(f, f.name)
    return FileResponse(str(zip_path), filename="分單結果.zip",
                        media_type="application/zip")

# ══════════════════════════════════════════════════════════════════════════════
#  開發者 API（密碼保護）
# ══════════════════════════════════════════════════════════════════════════════

def require_dev_token(request: Request):
    token = request.headers.get("X-Dev-Token", "")
    if not token or not verify_dev_password(token):
        raise HTTPException(401, "未授權")

@app.post("/api/dev/login")
async def dev_login(password: str = Form(...)):
    if not verify_dev_password(password):
        raise HTTPException(401, "密碼錯誤")
    return {"ok": True, "token": password}

@app.get("/api/dev/config")
async def get_config(request: Request, _=Depends(require_dev_token)):
    return load_config()

@app.post("/api/dev/price-map")
async def update_price_map(request: Request, _=Depends(require_dev_token)):
    body = await request.json()
    cfg = load_config()
    cfg["price_map"] = body
    save_config(cfg)
    return {"ok": True}

@app.post("/api/dev/product-map")
async def update_product_map(request: Request, _=Depends(require_dev_token)):
    """商品名稱+品項 → 分類名稱 的對照表"""
    body = await request.json()
    cfg = load_config()
    cfg["product_map"] = body
    save_config(cfg)
    return {"ok": True}

@app.post("/api/dev/gift-rules")
async def update_gift_rules(request: Request, _=Depends(require_dev_token)):
    body = await request.json()
    cfg = load_config()
    cfg["gift_rules"] = body
    save_config(cfg)
    return {"ok": True}

@app.post("/api/dev/parse-excel")
async def parse_excel(request: Request, file: UploadFile = File(...), _=Depends(require_dev_token)):
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "只接受 .xlsx / .xls 檔案")
    try:
        import pandas as pd
        from io import BytesIO
        content = await file.read()
        df = pd.read_excel(BytesIO(content))

        if '售價' not in df.columns or '商品名稱' not in df.columns:
            raise HTTPException(400, "找不到「售價」或「商品名稱」欄位，請確認是 MeepShop 匯出格式")

        item_cols = ['品項一', '品項二', '組合擇一', '品項', '商品', '品項擇一']
        for col in item_cols:
            if col not in df.columns:
                df[col] = ''

        def merge_items(row):
            vals = [str(row[c]).strip() for c in item_cols
                    if c in row.index and str(row[c]).strip() not in ('', 'nan', 'NaN')]
            return ' / '.join(vals) if vals else ''

        df['_品項'] = df.apply(merge_items, axis=1)
        df = df[['商品名稱', '售價', '_品項']].dropna(subset=['售價']).fillna('')
        df['售價'] = df['售價'].astype(int)
        df = df.sort_values(['商品名稱', '_品項'])
        # 以 商品名稱+品項 去重
        df = df.drop_duplicates(subset=['商品名稱', '_品項'])

        cfg = load_config()
        existing_map = cfg.get("product_map", {})

        rows = []
        for _, row in df.iterrows():
            name  = str(row['商品名稱'])
            items = str(row['_品項'])
            price = str(int(row['售價']))
            key   = f"{name}|||{items}"
            # 優先用已儲存的 product_map，其次用內建自動對照
            kind = (existing_map.get(key, {}).get("kind", "")
                    or AUTO_PRODUCT_MAP.get(key, ""))
            rows.append({
                "key":          key,
                "product_name": name,
                "items":        items,
                "price":        price,
                "kind":         kind,
                "is_new":       key not in existing_map
            })
        return {"rows": rows, "total": len(rows)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"解析失敗：{e}")
async def parse_excel(request: Request, file: UploadFile = File(...), _=Depends(require_dev_token)):
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "只接受 .xlsx / .xls 檔案")
    try:
        import pandas as pd
        from io import BytesIO
        content = await file.read()
        df = pd.read_excel(BytesIO(content))

        if '售價' not in df.columns or '商品名稱' not in df.columns:
            raise HTTPException(400, "找不到「售價」或「商品名稱」欄位，請確認是 MeepShop 匯出格式")

        # P欄之後所有品項欄位，合併成一個「品項」
        item_cols = ['品項一', '品項二', '組合擇一', '品項', '商品', '品項擇一']
        for col in item_cols:
            if col not in df.columns:
                df[col] = ''

        def merge_items(row):
            vals = [str(row[c]).strip() for c in item_cols
                    if c in row.index and str(row[c]).strip() not in ('', 'nan', 'NaN')]
            return ' / '.join(vals) if vals else ''

        df['_品項合併'] = df.apply(merge_items, axis=1)
        df = df[['商品名稱', '售價', '_品項合併']].dropna(subset=['售價'])
        df['售價'] = df['售價'].astype(int)
        df = df.sort_values(['售價', '商品名稱']).fillna('')

        cfg = load_config()
        existing_map = cfg.get("price_map", {})

        seen_prices = set()
        rows = []
        for _, row in df.iterrows():
            price    = str(int(row['售價']))
            name     = str(row['商品名稱'])
            items    = str(row['_品項合併'])
            kind     = existing_map.get(price, {}).get("kind", "")
            is_first = price not in seen_prices
            if is_first:
                seen_prices.add(price)
            rows.append({
                "price":        price,
                "product_name": name,
                "items":        items,
                "kind":         kind,
                "is_new":       price not in existing_map,
                "is_first":     is_first
            })
        return {"rows": rows, "total": len(seen_prices)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"解析失敗：{e}")

@app.post("/api/dev/change-password")
async def change_password(request: Request, _=Depends(require_dev_token)):
    body = await request.json()
    cur = body.get("current", "")
    new = body.get("new", "")
    if not verify_dev_password(cur):
        raise HTTPException(401, "目前密碼錯誤")
    if len(new) < 6:
        raise HTTPException(400, "新密碼至少 6 碼")
    cfg = load_config()
    cfg["dev_password_hash"] = hashlib.sha256(new.encode()).hexdigest()
    save_config(cfg)
    return {"ok": True}
