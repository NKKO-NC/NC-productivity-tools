# Excel Column Helper / Excel 欄位對照工具

這是這個 repo 第一個正式上線的小工具，也是目前的 PWA 範例基準。  
This is the first shipped tool in the repo and the current baseline PWA example.

## 功能 / What It Does

- 將 Excel 欄位字母轉成數字序號
- 展開起始欄位到結束欄位的區間
- 支援 `A` 到 `XFD`
- 提供中英雙語介面
- 可安裝成 PWA，支援基本離線快取

## 檔案 / Files

- `index.html`：工具頁面 / tool page
- `app.js`：工具邏輯與文案 / tool logic and copy

## 為什麼它重要 / Why It Matters

這個工具可以當作後續新增工具的基準樣板，因為它已經具備：

- 共用樣式 / shared styling
- 雙語文案 / bilingual copy
- 可獨立抽出的純邏輯 / pure logic that can later be extracted or tested
- PWA 發布能力 / installable PWA behavior

## 技術標籤 / Tech Tags

- `#PWA`
- `#HTML`
- `#VanillaJS`
- `#Excel`
- `#Offline`

## 限制 / Limits

這個工具目前適合靜態部署、前端互動與離線查表。  
如果未來需求變成原生多視窗、系統級檔案權限、背景常駐或桌面整合，GitHub Pages + PWA 會有明顯限制。
