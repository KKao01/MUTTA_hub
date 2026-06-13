# MUTTA·HUB — 版面編輯 + 文字框 + 持久化（Railway Volume）

## 功能
- 主頁：3×7 可拖曳字卡 + 最下方 1×5 長條 + 自由定位文字框，全部右上「✎ 編輯」用 dev 密碼進入編輯。
- 字卡：ICON/大標/小標/2框格/背光/連結/顯示/位置。長條：主標題/連結/背光/位置。文字框：內容/字級/粗體/對齊/顏色/底色/位置。
- 背景切換（影片/Shader/無）在 /dev；影片上傳 20MB 上限。
- Brand Gallery 已移除。

## 持久化（重點）
編輯存檔寫進 `config.json`，上傳影片寫進 `media/bg.mp4`。
路徑由環境變數 `DATA_DIR` 決定：
- 沒設 `DATA_DIR` → 退回 repo 根目錄（本機開發照舊）。
- 設 `DATA_DIR=/data` 並在 Railway 掛 Volume 到 `/data` → 設定與影片存進 Volume，**重新部署不會被洗掉**。
首次啟動若 Volume 內沒有 config.json，會用 repo 內已 commit 的 config.json 當種子（保留密碼/版面）。

## Railway 設定步驟（接上 Volume）
1. Railway → 你的 MUTTA_hub 服務。
2. 掛一個 Volume，Mount Path 設 `/data`
   （若你之前為相簿開過 Volume，可重用：把它的 Mount Path 改成 /data，或把 DATA_DIR 設成它現有的掛載路徑）。
3. Variables 加環境變數：`DATA_DIR` = `/data`
4. 重新部署。第一次啟動會把 repo 的 config.json 種進 /data/config.json，之後所有線上編輯/上傳都存在 Volume。
5. 驗證：主頁編輯→存檔→Railway 手動 Redeploy→回主頁看改動還在＝成功。

## 變動檔案（解壓覆蓋 repo 根目錄）
app/main.py、config.json、templates/index.html、templates/dev.html、
static/js/main.js、static/js/dev.js、static/css/main.css、static/bg.mp4

## 本機測試
解壓→蓋進 D:\MUTTA_hub→`uvicorn app.main:app --reload`→ http://localhost:8000
（本機不設 DATA_DIR 即可，config 會寫在 repo；上線再靠 Volume 持久化）
