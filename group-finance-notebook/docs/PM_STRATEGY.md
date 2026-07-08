# PM 路線與交付策略

## 1. 產品策略

第一版不追求完整財務分析，而是先把資料地基與圖像工作流做穩。核心假設是：只要公司識別、時間版本、投資關係圖三者正確，收入損益分析與關係人交易都可以在後續版本逐步長上去。

## 2. Phase 1 成功標準

Phase 1 成功不是功能數量多，而是做到：

- 公司主檔可信。
- 投資架構可信。
- 時間切換可信。
- 匯入匯出可信。
- 修改歷史可信。

總驗收句：

```text
同一份本機資料，在選取 2026-03-31 與 2026-06-30 時，可以正確顯示不同的公司投資架構，且所有修改都不覆蓋歷史資料。
```

## 3. 建議里程碑

### M0 文件與樣本資料

交付：

- 產品規格。
- 資料模型規格。
- UI 規格。
- QA 規格。
- 小型測試資料集。

驗收：

- 使用者確認 Phase 1 範圍。
- 使用者確認 metadata 欄位。
- 使用者確認投資架構欄位。

### M1 資料核心

交付：

- SQLite schema。
- company identity。
- company alias。
- company profile SCD。
- investment edge SCD。
- source batch。
- 基礎 resolver。

驗收：

- 公司代碼、簡稱、全稱可互查。
- 同公司改名可保留歷史。
- 投資關係可依日期查詢。

### M2 匯入 Preview

交付：

- Excel paste parser。
- CSV parser。
- 欄位 mapping UI。
- validation result。
- preview changes。

驗收：

- 錯誤資料不入庫。
- 匯入前可看到新增/更新項目。
- 匯入後可追 source_batch。

### M3 圖像工作台

交付：

- 公司圖卡。
- 投資連線。
- 右側公司編輯。
- 右側投資線編輯。
- as-of date 切換。
- 搜尋公司。
- 拖曳節點與布局保存。

驗收：

- 3/31 與 6/30 顯示不同架構。
- 使用者調整位置後不被洗掉。
- 點卡片與線都能編輯。

### M4 匯出還原

交付：

- SQLite DB 匯出。
- CSV 匯出。
- TXT schema 匯出。
- DB/CSV 重新匯入。

驗收：

- 匯出後重新匯入結果一致。
- as-of date 查詢結果一致。
- 圖面布局可還原。

### M5 Phase 1 hardening

交付：

- QA 修正。
- 效能調整。
- 錯誤訊息整理。
- 基礎操作說明。

驗收：

- 100 公司 / 200 投資線流暢。
- 無網路可完整操作。
- 核心 QA 全通過。

## 4. Phase 2 預備項目

Phase 1 只保留接口，不實作完整功能：

- financial_metric_scd。
- company card 財務摘要區。
- 損益分色 style rule。
- 關係人交易 edge type。
- 交易關係 parser rule。

Phase 2 可拆成：

```text
Phase 2A: 收入損益資料輸入與顯示
Phase 2B: 損益視覺分色
Phase 2C: 關係人交易資料模型
Phase 2D: 關係人交易圖與判定 rule
```

## 5. 技術建議

### 5.1 建議方案

```text
Tauri + React + SQLite
```

理由：

- 本機桌面 App 體驗較完整。
- SQLite 適合本機資料與匯出。
- React graph library 適合互動式圖面。
- Tauri 體積較小，適合純本機工具。

### 5.2 備選方案

```text
Python + PySide6 + SQLite
```

優點：

- 資料處理與打包直覺。
- Python 對 Excel/CSV 處理成熟。

缺點：

- 大型互動圖面體驗可能較費工。

## 6. 主要風險

### 6.1 公司識別混亂

風險：

- 簡稱重複。
- 公司改名。
- 代碼缺漏。
- Excel 輸入不一致。

對策：

- alias 模型。
- resolver preview。
- 衝突時要求使用者確認。

### 6.2 時間模型設計錯誤

風險：

- 修改資料時覆蓋歷史。
- 無法回看過去架構。

對策：

- SCD 模型。
- 修改時新增版本。
- QA 強制測 3/31 與 6/30。

### 6.3 圖面大型化後難讀

風險：

- 公司多時圖面混亂。

對策：

- 搜尋聚焦。
- 區域與主營項目篩選。
- 上下游聚焦。
- 布局記憶。

### 6.4 匯入過度自動化

風險：

- 自動 mapping 錯誤導致資料污染。

對策：

- 必須 preview。
- 可手動調整 mapping。
- blocking error 不入庫。

## 7. 決策紀錄

### 7.1 收入損益分析延後

收入損益分析項目保留接口，列為 Phase 2。Phase 1 不實作完整損益分析，以避免核心資料模型與投資架構驗證被稀釋。

### 7.2 優先建立投資架構圖

Phase 1 優先驗證：

```text
company resolver + investment edge SCD + as-of date graph
```

這是後續所有功能的地基。

