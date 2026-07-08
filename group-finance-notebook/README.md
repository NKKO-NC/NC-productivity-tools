# 集團財務圖像筆記本

本專案是一個專為集團財務人員設計的純本機工具。這個版本已實作一個可直接啟動的 Phase 1 MVP，重點落在 SQLite 資料核心、as-of date 架構圖、公司識別、貼上匯入預覽，以及 CSV/TXT/DB 匯出。

## 已實作內容

- SQLite schema：`company_identity`、`company_alias`、`company_profile_scd`、`investment_edge_scd`、`source_batch`、`graph_layout`、`rule_definition`
- 公司代碼 / 簡稱 / 全稱 resolver
- 公司 profile 與投資關係的 SCD 版本寫入
- `2026-03-31` 與 `2026-06-30` as-of date 架構切換
- 本機單頁工作台：搜尋、圖卡、投資線、明細、右側編輯表單
- Excel 貼上式 tab 分隔匯入預覽與套用
- CSV / TXT schema / DB 匯出
- 內建 demo 資料與自動化測試

## 最簡單的開啟方式

如果你不是工程使用者，不需要進 `gfnb\static` 找檔案，也不用自己打指令。

直接在專案資料夾裡雙擊：

- [啟動集團財務圖像筆記本.cmd](C:/Users/User/工具/生產力工具/group-finance-notebook/啟動集團財務圖像筆記本.cmd)
- [重設Demo並啟動.cmd](C:/Users/User/工具/生產力工具/group-finance-notebook/重設Demo並啟動.cmd)

系統會自動：

- 啟動本機服務
- 開啟瀏覽器
- 進入 `http://127.0.0.1:8765`

關閉啟動後跳出的黑色視窗，就會停止系統。

## 指令啟動方式

使用內建 Python runtime：

```powershell
C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run.py
```

預設會在 `http://127.0.0.1:8765` 啟動，資料庫存於 [data/group_finance_notebook.db](C:/Users/User/工具/生產力工具/group-finance-notebook/data/group_finance_notebook.db)。

若要重設為內建 demo 資料：

```powershell
C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe run.py --reset-demo
```

## 測試

```powershell
C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests -v
```

## 文件索引

- [產品規格](docs/PRODUCT_SPEC.md)
- [資料模型規格](docs/DATA_MODEL_SPEC.md)
- [UI 規格](docs/UI_SPEC.md)
- [匯入匯出規格](docs/IMPORT_EXPORT_SPEC.md)
- [規則與解析器規格](docs/RULE_ENGINE_SPEC.md)
- [QA 測試規格](docs/QA_SPEC.md)
- [PM 路線與交付策略](docs/PM_STRATEGY.md)
