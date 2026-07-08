# 匯入匯出規格

## 1. 匯入原則

- 所有匯入都必須經過 preview。
- 所有匯入都必須產生 `source_batch_id`。
- 錯誤資料不得直接入庫。
- 欄位 mapping 應可由使用者調整。
- 匯入後必須可回溯來源批次。

## 2. 支援輸入

Phase 1 支援三種輸入：

1. 特定 schema 匯入。
2. Excel 複製貼上。
3. UI 卡片編輯。

## 3. 特定 schema 匯入

支援格式：

- CSV
- TXT schema
- SQLite DB

建議檔案組：

```text
manifest.json
companies.csv
company_aliases.csv
company_profiles.csv
investment_edges.csv
rules.json
```

### 3.1 manifest.json

```json
{
  "schema_version": "0.1",
  "exported_at": "2026-07-09T00:00:00+08:00",
  "app": "group-finance-notebook",
  "files": [
    "companies.csv",
    "company_aliases.csv",
    "company_profiles.csv",
    "investment_edges.csv",
    "rules.json"
  ]
}
```

### 3.2 companies.csv

欄位：

```text
company_id
created_at
archived_at
```

### 3.3 company_aliases.csv

欄位：

```text
alias_id
company_id
alias_type
alias_value
normalized_value
valid_from
valid_to
priority
created_at
source_batch_id
```

### 3.4 company_profiles.csv

欄位：

```text
profile_id
company_id
valid_from
valid_to
company_code
short_name
full_name
main_business
symbol_code
region
currency
note
created_at
updated_at
source_batch_id
```

### 3.5 investment_edges.csv

欄位：

```text
edge_id
parent_company_id
child_company_id
change_date
valid_from
valid_to
parent_company_code_raw
parent_short_name_raw
parent_full_name_raw
child_company_code_raw
child_short_name_raw
child_full_name_raw
investment_shares
child_total_shares
ownership_pct
note
created_at
updated_at
source_batch_id
```

## 4. Excel 貼上匯入

### 4.1 支援資料類型

第一版支援：

- 公司 metadata
- 投資架構
- metadata + 投資架構混合表

### 4.2 欄位自動辨識

系統應能辨識以下中文欄位別名：

```text
公司代碼: company_code, 公司代號, 代碼
公司簡稱: short_name, 簡稱
公司全稱: full_name, 公司名稱, 全名
公司主營項目: main_business, 主營項目, 營業項目
代號: symbol_code, 股票代號, 代號
所在地區: region, 地區, 國家, 國別
使用幣別: currency, 幣別
上層公司代碼: parent_company_code, 母公司代碼, 上層代碼
上層公司簡稱: parent_short_name, 母公司簡稱, 上層簡稱
上層公司全稱: parent_full_name, 母公司名稱, 上層公司名稱
下層公司代碼: child_company_code, 子公司代碼, 下層代碼
下層公司簡稱: child_short_name, 子公司簡稱, 下層簡稱
下層公司全稱: child_full_name, 子公司名稱, 下層公司名稱
投資股數: investment_shares, 持有股數
下層總股數: child_total_shares, 總股數
佔股比: ownership_pct, 持股比例, 持股比, %
變更日期: change_date, 生效日期, 日期
```

### 4.3 百分比解析

輸入值轉換：

```text
80% -> 0.8
0.8 -> 0.8
80 -> 0.8
100 -> 1
```

若值大於 100 或小於 0，需標示錯誤。

### 4.4 日期解析

Phase 1 必須支援：

```text
2026-03-31
2026/03/31
2026/3/31
```

Phase 1.5 可支援民國年。

## 5. UI 卡片編輯

UI 編輯也必須走與匯入相同的資料服務：

```text
表單資料
-> validation
-> resolver
-> versioning
-> DB write
```

不得讓 UI 編輯繞過版本控制。

## 6. 匯出

Phase 1 支援三種輸出：

1. TXT schema。
2. SQLite DB。
3. CSV 檔案組。

### 6.1 TXT schema

建議使用 JSON Lines：

```text
companies.jsonl
company_aliases.jsonl
company_profiles.jsonl
investment_edges.jsonl
rules.jsonl
```

優點：

- 人可讀。
- 機器易解析。
- 一筆錯誤不影響整檔讀取。

### 6.2 SQLite DB

匯出完整 `.db` 檔，包含：

- 所有資料表。
- source batch。
- rules。
- graph layout。

### 6.3 CSV 檔案組

匯出：

```text
manifest.json
companies.csv
company_aliases.csv
company_profiles.csv
investment_edges.csv
rules.csv
graph_layout.csv
```

## 7. 匯出還原驗收

匯出後重新匯入，必須符合：

- 公司數一致。
- alias 對應一致。
- metadata 版本一致。
- 投資架構版本一致。
- as-of date 查詢結果一致。
- 圖面布局在同一 `view_key` 下可還原。

