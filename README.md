# NC 生產力工具站 / NC Productivity Tools

雙語公開倉庫，專門收錄小而實用的生產力工具。  
A bilingual public repo for small, practical productivity tools.

## 專案定位 / Project Focus

- 以工具為核心，而不是以技術分類為核心
- 每個工具都能獨立維護、獨立擴充
- 首頁負責功能導讀，工具資料夾負責實作與說明
- 中文主體、英文對照，避免 repo 外觀過度英文化
- 以 GitHub Pages + PWA 為第一階段發布方式

## 發布方式 / Deployment

- `GitHub Pages`：公開靜態站點入口
- `PWA`：可安裝、可離線快取、適合輕量工具

## 功能目錄 / Tool Directory

- `Excel 欄位對照工具 / Excel Column Helper`
  連結：`tools/excel-column-helper/`
  標籤：`#PWA #HTML #VanillaJS #Excel #Offline`
  用途：Excel 欄位字母與序號快速對照

## 結構 / Structure

```text
assets/
  css/                  共用樣式 / Shared styles
  js/                   共用腳本 / Shared scripts
docs/
  repo-structure.md     倉庫規範 / Repo notes
tools/
  excel-column-helper/  第一個正式工具 / First shipped tool
index.html              首頁導覽 / Homepage
```

## 第一個工具 / First Tool

- `Excel Column Helper / Excel 欄位對照工具`
  把 Excel 欄位字母，例如 `A`、`Z`、`XFD`，轉成對應序號並展開區間。  
  Convert Excel column letters such as `A`, `Z`, or `XFD` into numeric positions and expand a range.

## 後續擴充 / Next Step

新增工具時，最少維持這組結構：

- `tools/<tool-slug>/index.html`
- `tools/<tool-slug>/app.js`
- `tools/<tool-slug>/README.md`

並在首頁補上一張工具卡，讓使用者能依功能而不是依技術來源找到它。  
Then add one homepage card so users can discover the tool by function rather than implementation detail.

## 標籤用途 / Tag Semantics

- `#PWA`：可安裝、可離線，但仍受瀏覽器沙箱限制
- `#HTML`：主要由靜態頁面構成，適合 GitHub Pages
- `#VanillaJS`：不依賴大型框架，方便維護與快速載入
- `#Offline`：已加入 service worker 快取

## 技術邊界 / Platform Limits

如果未來工具需要以下能力，就要及早評估是否繼續放在 GitHub Pages / PWA：

- 原生多視窗或浮動視窗
- 深度本機檔案系統權限
- 背景常駐工作
- 系統層通知整合以外的桌面功能
- 高度即時同步或長連線桌面體驗
