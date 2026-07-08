# 資料模型規格

## 1. 設計原則

- 所有資料純本機保存。
- SQLite 作為 Phase 1 建議主儲存格式。
- 公司識別與公司名稱別名分離。
- 公司 metadata 使用 SCD 模型保存版本。
- 投資架構使用 edge SCD 模型保存版本。
- 匯入原始值需保留，解析後 id 也需保留。
- 收入損益資料僅保留 Phase 2 接口。

## 2. 核心概念

### 2.1 company_id

`company_id` 是系統內部穩定識別碼。公司代碼、公司簡稱、公司全稱都不是唯一真相，而是指向 company_id 的 alias。

### 2.2 alias

同一家公司可以有多個 alias：

- 公司代碼
- 公司簡稱
- 公司全稱
- 舊名稱
- 自訂名稱

當簡稱重複或命中多家公司時，系統不得自動亂配，必須要求使用者確認。

### 2.3 effective time

資料在現實世界生效的日期。例如投資關係在 2026-03-31 生效。

### 2.4 system time

使用者在系統中建立或修改資料的時間。例如使用者在 2026-05-10 補登 2026-03-31 的持股變更。

Phase 1 至少需要保存 `created_at` 與 `updated_at`。若工程複雜度允許，應支援完整 bitemporal 紀錄。

## 3. 建議資料表

### 3.1 company_identity

```sql
CREATE TABLE company_identity (
  company_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  archived_at TEXT
);
```

### 3.2 company_alias

```sql
CREATE TABLE company_alias (
  alias_id TEXT PRIMARY KEY,
  company_id TEXT NOT NULL,
  alias_type TEXT NOT NULL,
  alias_value TEXT NOT NULL,
  normalized_value TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  priority INTEGER NOT NULL DEFAULT 100,
  created_at TEXT NOT NULL,
  source_batch_id TEXT,
  FOREIGN KEY (company_id) REFERENCES company_identity(company_id)
);
```

`alias_type` 建議值：

- `company_code`
- `short_name`
- `full_name`
- `stock_code`
- `former_name`
- `custom`

### 3.3 company_profile_scd

```sql
CREATE TABLE company_profile_scd (
  profile_id TEXT PRIMARY KEY,
  company_id TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  company_code TEXT,
  short_name TEXT,
  full_name TEXT,
  main_business TEXT,
  symbol_code TEXT,
  region TEXT,
  currency TEXT,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  source_batch_id TEXT,
  FOREIGN KEY (company_id) REFERENCES company_identity(company_id)
);
```

metadata 欄位第一版：

- 公司代碼
- 公司簡稱
- 公司全稱
- 公司主營項目
- 代號
- 所在地區
- 使用幣別

### 3.4 investment_edge_scd

```sql
CREATE TABLE investment_edge_scd (
  edge_id TEXT PRIMARY KEY,
  parent_company_id TEXT NOT NULL,
  child_company_id TEXT NOT NULL,
  change_date TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  parent_company_code_raw TEXT,
  parent_short_name_raw TEXT,
  parent_full_name_raw TEXT,
  child_company_code_raw TEXT,
  child_short_name_raw TEXT,
  child_full_name_raw TEXT,
  investment_shares NUMERIC,
  child_total_shares NUMERIC,
  ownership_pct NUMERIC,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  source_batch_id TEXT,
  FOREIGN KEY (parent_company_id) REFERENCES company_identity(company_id),
  FOREIGN KEY (child_company_id) REFERENCES company_identity(company_id)
);
```

`ownership_pct` 建議用 0 到 1 的小數保存。顯示時再轉成百分比。

### 3.5 source_batch

```sql
CREATE TABLE source_batch (
  source_batch_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  source_name TEXT,
  imported_at TEXT NOT NULL,
  row_count INTEGER,
  status TEXT NOT NULL,
  note TEXT
);
```

`source_type` 建議值：

- `excel_paste`
- `csv_import`
- `txt_schema_import`
- `ui_edit`
- `db_import`

### 3.6 graph_layout

```sql
CREATE TABLE graph_layout (
  layout_id TEXT PRIMARY KEY,
  company_id TEXT NOT NULL,
  view_key TEXT NOT NULL,
  x NUMERIC NOT NULL,
  y NUMERIC NOT NULL,
  pinned INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (company_id) REFERENCES company_identity(company_id)
);
```

圖面切換 as-of date 時，應優先沿用相同 `view_key` 的節點位置。

### 3.7 rule_definition

```sql
CREATE TABLE rule_definition (
  rule_id TEXT PRIMARY KEY,
  rule_type TEXT NOT NULL,
  name TEXT NOT NULL,
  config_json TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  priority INTEGER NOT NULL DEFAULT 100,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

`rule_type` 建議值：

- `parser`
- `resolver`
- `edge`
- `style`
- `validation`

### 3.8 financial_metric_scd Phase 2 接口

Phase 1 可先建立接口或保留 migration，不要求 UI 實作。

```sql
CREATE TABLE financial_metric_scd (
  metric_record_id TEXT PRIMARY KEY,
  company_id TEXT NOT NULL,
  period_end TEXT NOT NULL,
  metric_code TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  amount NUMERIC,
  currency TEXT,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  created_at TEXT NOT NULL,
  source_batch_id TEXT,
  FOREIGN KEY (company_id) REFERENCES company_identity(company_id)
);
```

Phase 2 預計項目：

- 營業收入
- 銷貨成本
- 營業費用
- 稅前淨利
- 其他自訂損益項目

## 4. 查詢需求

### 4.1 公司互查

輸入公司代碼、公司簡稱或公司全稱，系統應：

1. normalize 輸入值。
2. 查詢 company_alias。
3. 若唯一命中，回傳 company_id。
4. 若多筆命中，要求使用者選擇。
5. 若無命中，允許建立新公司或標示 unresolved。

### 4.2 as-of 公司 profile

查詢條件：

```text
valid_from <= as_of_date
AND (valid_to IS NULL OR valid_to > as_of_date)
```

### 4.3 as-of 投資架構

查詢條件：

```text
valid_from <= as_of_date
AND (valid_to IS NULL OR valid_to > as_of_date)
```

### 4.4 歷史不可覆蓋

修改既有資料時，應：

1. 將舊紀錄 `valid_to` 設為新變更生效日。
2. 新增一筆新紀錄。
3. 保留 source_batch 或 ui_edit 紀錄。

