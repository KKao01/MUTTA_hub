# 分單系統 — 網頁版

FastAPI + 原生 HTML/CSS/JS，無前端框架依賴。

---

## 檔案結構

```
web_split/
├── app/
│   ├── main.py          # FastAPI 後端（所有 API）
│   └── core_logic.py    # 分單底層邏輯（從 run_script_v6 移植）
├── static/
│   ├── css/main.css     # 主頁樣式
│   ├── css/dev.css      # 開發者頁樣式（深色主題）
│   ├── js/main.js       # 主頁邏輯
│   └── js/dev.js        # 開發者介面邏輯
├── templates/
│   ├── index.html       # 主頁（一般使用者）
│   └── dev.html         # 開發者介面
├── requirements.txt
├── railway.toml         # Railway 部署設定
├── start.sh             # 本機啟動腳本
└── README.md
```

---

## 本機測試

```bash
cd web_split
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 開啟 http://localhost:8000
```

---

## 部署到 Railway（推薦，最快）

1. 前往 https://railway.app 並登入
2. 點 **New Project → Deploy from GitHub repo**
3. 把這個資料夾推上 GitHub，選擇該 repo
4. Railway 自動偵測 Python、安裝套件、啟動
5. 設定 **Custom Domain** 或使用 Railway 給的域名

> railway.toml 已設定好 startCommand，直接推就能跑。

---

## 開發者模式

### 觸發方式（隱藏入口）
在主頁 **📦 圖示上連點 5 下**，自動跳轉至 `/dev`。

### 預設密碼
```
admin1234
```
第一次進入後立即至「修改密碼」更換。

### 功能
| 分頁 | 內容 |
|------|------|
| 商品售價對照 | 新增 / 編輯 / 刪除 售價→分類 對應 |
| 修改密碼 | 更換開發者密碼（SHA-256 雜湊存儲） |
| 說明 | 操作說明、安全說明 |

---

## 安全設計

| 保護層 | 方式 |
|--------|------|
| 開發者入口 | 無任何連結/按鈕，只有隱藏手勢（5 連點） |
| API 驗證 | 所有 `/api/dev/*` 需帶 `X-Dev-Token` Header |
| 密碼存儲 | SHA-256 雜湊，不存明文 |
| 進一步加強 | 可在 Nginx/Cloudflare 限制 `/dev` 路徑的 IP 白名單 |

---

## 修改贈品邏輯

編輯 `app/core_logic.py` 的 `gift()` 函式，改完重新部署即生效。

---

## 常見問題

**Q：上傳的 PDF 存放在哪？**
A：`uploads/` 目錄（依任務 ID 分資料夾）。Railway 重啟後會清空，
   若需永久保存可串接 S3 或 Railway Volume。

**Q：Railway 免費版夠用嗎？**
A：免費版每月有 $5 額度，內部工具完全夠用。
   若需要儲存 Volume（保留輸出 PDF），需升級至 Hobby 方案（$5/月）。
