# 規則與解析器規格

## 1. 設計目的

本工具未來會支援收入損益分析、關係人交易、不同視覺分色與不同連線類型。因此 Phase 1 不應將連線、解析、顏色、驗證邏輯全部寫死在 UI 中。

Phase 1 應至少建立 rule-driven 的概念與資料結構，讓未來可以新增 rule，而不是重寫核心圖面。

## 2. 規則類型

### 2.1 parser rule

用途：

- 欄位名稱 mapping。
- 日期格式解析。
- 百分比解析。
- 數字格式解析。

範例：

```json
{
  "field": "ownership_pct",
  "aliases": ["佔股比", "持股比例", "持股比", "%"],
  "parser": "percentage"
}
```

### 2.2 resolver rule

用途：

- 公司識別。
- alias 優先順序。
- 衝突處理。

預設順序：

```text
1. company_code
2. full_name
3. short_name
4. former_name
5. custom
```

若短名稱命中多家公司，必須要求使用者確認。

### 2.3 edge rule

用途：

- 定義圖面連線類型。
- 定義連線方向。
- 定義連線 label。

Phase 1 預設 edge：

```json
{
  "edge_type": "investment",
  "direction": "parent_to_child",
  "label": "ownership_pct",
  "source_table": "investment_edge_scd"
}
```

Phase 2 可加入：

```text
related_party_trade
guarantee
loan
service_transaction
purchase_sale_transaction
```

### 2.4 style rule

用途：

- 地區分色。
- 主營項目分色。
- 持股比例線寬。
- 資料缺漏警示。

Phase 1 預設：

```json
{
  "rule_type": "style",
  "target": "company_node",
  "field": "region",
  "style": "fill_color_by_category"
}
```

Phase 2 保留：

```text
profit_loss_color
revenue_size
related_party_edge_color
```

### 2.5 validation rule

用途：

- 必填欄位驗證。
- 日期格式驗證。
- 百分比合理性驗證。
- 公司 alias 衝突偵測。
- 投資架構循環警示。

Phase 1 預設驗證：

- 公司至少需有代碼、簡稱、全稱其中之一。
- 投資關係必須有上層公司與下層公司。
- 上層公司不得等於下層公司。
- 佔股比需介於 0 到 1。
- 投資股數不得小於 0。
- 下層總股數不得小於 0。
- 同一 as-of date、同一上下層公司若有多筆有效投資線，需警示。

## 3. Parser pipeline

匯入與 UI 編輯都應進入同一條 pipeline：

```text
raw input
-> parse table or form
-> field mapping
-> normalize values
-> resolve companies
-> validate records
-> preview changes
-> apply versioned write
```

## 4. Preview change model

匯入套用前應產生預覽：

```text
新增公司
更新公司 metadata
新增 alias
新增投資關係
關閉舊投資關係版本
unresolved 公司
validation errors
warnings
```

只有無 blocking error 時才可套用。

## 5. 錯誤等級

### 5.1 blocking error

不得入庫：

- 無法解析日期。
- 投資關係缺少上層或下層公司。
- 同一欄位 mapping 重複且無法判斷。
- 佔股比超出範圍。

### 5.2 warning

可入庫但需提示：

- 公司缺少全稱。
- 公司缺少所在地區。
- 公司簡稱重複但使用者已確認。
- 投資股數與佔股比推算結果不一致。

### 5.3 info

一般資訊：

- 新增公司。
- 新增 alias。
- 建立新版本。

