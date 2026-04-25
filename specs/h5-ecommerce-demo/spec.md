# H5 商品展示與訂單預埋（第一期）

## Goal

為一個 demo 用的 H5 電商網站建立第一期：前端為單頁 SPA，僅展示商品列表 + 用戶名登錄 + 客服入口；後端用 FastAPI 提供商品 API；同時在 SQLite 預埋訂單與物流數據，作為第二期智能客服查詢的數據底盤。

> 第二期（本 spec **不**實作）：智能客服對話功能，可基於訂單資料查詢物流。

## Tech Stack

- **後端**：Python 3.12 + FastAPI + SQLAlchemy 2.x + SQLite（檔案 `./demo.db`）
- **前端**：Vue 3 + Vite（JavaScript，無 TypeScript）
- **測試**：pytest + FastAPI TestClient + in-memory SQLite（`sqlite:///:memory:`）
- **文案語言**：頁面 UI 與 seed data 全部用簡體中文

## 數據模型

### `products` 表

| 欄位 | 類型 | 約束 |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| `name` | TEXT | NOT NULL |
| `sku` | TEXT | NOT NULL, **UNIQUE** |
| `stock` | INTEGER | NOT NULL, CHECK >= 0 |
| `price` | NUMERIC(10, 2) | NOT NULL, CHECK > 0 |
| `image_url` | TEXT | NOT NULL（商品配圖 URL） |

### `orders` 表

| 欄位 | 類型 | 約束 |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| `username` | TEXT | NOT NULL |
| `product_sku` | TEXT | NOT NULL, FK → `products.sku` |
| `product_name` | TEXT | NOT NULL（snapshot，下單當下商品名） |
| `unit_price` | NUMERIC(10, 2) | NOT NULL（snapshot，下單當下單價） |
| `quantity` | INTEGER | NOT NULL, CHECK >= 1 |
| `total_amount` | NUMERIC(10, 2) | NOT NULL, **必滿足** `total_amount = unit_price × quantity` |
| `logistics_info` | TEXT | NOT NULL，存 JSON 字串（schema 見下） |

### `logistics_info` JSON Schema

```json
{
  "recipient": "string",
  "address": "string",
  "phone": "string",
  "tracking_no": "string",
  "courier": "string",
  "current_status": "已下单 | 已发货 | 运输中 | 已签收",
  "tracking_history": [
    {
      "timestamp": "ISO8601 string, e.g. 2026-04-15T10:00:00",
      "status": "已下单 | 已发货 | 运输中 | 已签收",
      "location": "string",
      "description": "string"
    }
  ]
}
```

**約束**：
- 7 個頂層欄位皆必填。
- `tracking_history` 至少 1 筆 event。
- `current_status` 必須等於 `tracking_history` 最後一筆的 `status`。
- `status` 枚舉值：`已下单` / `已发货` / `运输中` / `已签收`。

## Public API（第一期）

### `GET /api/products`

回傳所有商品。

**Response 200**：
```json
[
  {"id": 1, "name": "蓝牙耳机·Pro", "sku": "AUDIO-001", "stock": 50, "price": "299.00",
   "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop&auto=format"},
  ...
]
```

> **本期僅此一個 endpoint**。其他 endpoint（如 `GET /api/orders?username=xxx`、`GET /api/orders/{id}`）留到第二期。

## 前端頁面（單頁 SPA）

### 結構（由上至下）

1. **頂部 Header**
   - 左側：站名「Demo 商城」
   - 右側：登錄區（兩種狀態互斥）
     - 未登錄：用戶名輸入框 + 「登录」按鈕
     - 已登錄：「欢迎，{username}」+「退出」按鈕

2. **商品列表（卡片網格）**
   - 每張卡片：商品圖（正方形）+ 商品名 + 價格 + 庫存（「剩余 N 件」）
   - 圖片用 `<img loading="lazy">` 從 `image_url` 載入

3. **右下角浮動客服按鈕**
   - 固定 `position: fixed; bottom: 20px; right: 20px`
   - 點擊彈出 toast「智能客服功能即将上线，敬请期待」（3 秒後消失）

### UI 文案（簡體中文，固定）

| 元素 | 文案 |
|---|---|
| 站名 | `Demo 商城` |
| 用戶名輸入 placeholder | `请输入用户名` |
| 登錄按鈕 | `登录` |
| 歡迎詞 | `欢迎，{username}` |
| 退出按鈕 | `退出` |
| 客服按鈕 | `客服` |
| 客服 toast | `智能客服功能即将上线，敬请期待` |
| 庫存標籤 | `剩余 {n} 件` |
| API 失敗 | `商品加载失败，请稍后重试` |
| 用戶名格式錯誤 | `用户名长度需为 1-20 位，仅允许字母、数字、中文、下划线` |
| localStorage 不可用 | `无法保存登录状态，请检查浏览器设置` |

## 驗收條件 (Acceptance Criteria)

### 後端 / 數據（pytest 自動驗證）

1. **產品 API 結構**：`GET /api/products` 回傳 HTTP 200，body 為 JSON list，每個元素含 `id` / `name` / `sku` / `stock` / `price` / `image_url` 六個鍵。
2. **Seed 商品數量**：應用啟動後（建表 + 種子），`products` 表共 **8** 筆資料。
3. **Seed 商品庫存皆 > 0**：本期無下單功能，無「售罄」概念，所有 seed 商品 `stock > 0`。
4. **SKU UNIQUE 約束**：嘗試插入 `sku` 重複的商品 → 應拋出 IntegrityError。
5. **Seed 訂單數量**：`orders` 表共 **5** 筆資料；其中 username 至少 **3 個不同用戶**。
6. **訂單金額一致性**：每一筆訂單滿足 `total_amount == unit_price × quantity`（NUMERIC(10,2)，兩位小數比較）。
7. **訂單 product_sku 有效性**：每一筆訂單的 `product_sku` 必存在於 `products` 表。
8. **訂單 product_name / unit_price 為快照**：訂單的 `product_name` 與 `unit_price` 等於下單時 products 表對應行的值（seed 時拷貝）。
9. **物流 JSON 結構**：每一筆訂單的 `logistics_info` 解析後含 7 個頂層欄位（`recipient` / `address` / `phone` / `tracking_no` / `courier` / `current_status` / `tracking_history`），無多餘無缺漏。
10. **物流 history 非空**：`tracking_history` 至少 1 筆 event，每筆 event 含 4 欄（`timestamp` / `status` / `location` / `description`）。
11. **物流狀態一致**：`current_status` 等於 `tracking_history` 最後一筆的 `status`。
12. **物流狀態枚舉**：所有 `status` 值 ∈ {`已下单`, `已发货`, `运输中`, `已签收`}。
13. **5 筆訂單覆蓋多種狀態**：5 筆訂單的 `current_status` 至少涵蓋 **3 種不同**狀態（如 `已签收` / `运输中` / `已发货`）。
14. **應用啟動可重入**：連續啟動兩次應用，products / orders 各表筆數仍為 8 / 5（seed 操作冪等）。

### 前端 / UI（手動冒煙測試，不在 pytest 範圍）

15. **未登錄即可看商品**：打開 `http://localhost:5173`（或 dev server URL），無需登錄即顯示 8 張商品卡片。
16. **登錄持久化**：輸入合法 username 點「登录」→ 頂部變「欢迎，{username}」；F5 刷新後仍保持登錄狀態。
17. **退出**：點「退出」→ 清除 localStorage → 回到未登錄狀態。
18. **用戶名校驗**：輸入空字串 / 超過 20 字 / 含非允許字符（如 `!@#`）→ 顯示錯誤文案，登錄失敗。
19. **客服按鈕**：右下角浮動按鈕在所有狀態（登錄/未登錄）皆可見；點擊彈 toast「智能客服功能即将上线，敬请期待」，3 秒後自動消失。
20. **API 失敗降級**：後端關閉時刷新頁面，顯示「商品加载失败，请稍后重试」。

## Key Decisions

- **Q1-C**：完整 SPA（Vue 3）+ 後端純 JSON API。理由：「單頁面」即 SPA。
- **Q2-A**：訂單為「一單一商品 + `quantity` 字段」結構。
- **Q3 廢除**：本期**無下單流程**，無庫存扣減邏輯；`stock` 字段僅作展示。
- **Q4-A**：訂單記錄 `unit_price` / `total_amount` 快照（seed 時寫死，不會變動）。
- **Q5/Q12-A**：物流 JSON 結構含 7 個頂層欄位 + `tracking_history` array。`current_status` 與 history 末筆 status 一致。
- **Q6-A**：登錄狀態純前端 localStorage；後端不存 user 表、不發 token、不驗證身份。
- **Q7 修正**：未登錄可瀏覽商品；本期登錄純為第二期客服身份識別預備（本期 UI 上登錄行為無實質後端效果）。
- **Q8 修正**：本期不展示「我的訂單」；訂單數據預埋給第二期客服查詢使用。
- **Q9-A**：客服入口為固定右下角浮動按鈕，點擊 toast「即將上線」。
- **Q10-A**：前端 Vue 3 + Vite。
- **Q11-A**：本期僅建訂單表 + seed data，**不**寫訂單 API；留到第二期。
- **語言**：頁面 UI 文案 + seed data 全部使用簡體中文（spec 文件本身延續對話風格）。
- **冪等 seed**：使用「表為空才插入」邏輯，避免重啟應用重複造數據。

## Non-goals

- 不做下單流程：無 `POST /api/orders`、無「立即購買」按鈕。
- 不做庫存扣減 / 庫存鎖定 / 防超賣。
- 不做認證 / 授權 / session / token / 密碼。
- 不做註冊 / 找回密碼 / 多因素認證。
- 不做訂單查詢頁面 / 「我的訂單」（第二期客服中實現）。
- 不做訂單 API endpoint：`GET /api/orders`、`GET /api/orders/{id}` 留第二期。
- 不做商品詳情頁 / 商品圖片 / 評論 / 分類 / 搜索 / 排序 / 分頁。
- 不做支付 / 物流真實對接。
- 不做客服對話實作（按鈕點擊只顯示 toast）。
- 不做時區處理（時間統一用 UTC ISO8601 字串）。
- 不做多語言切換（固定簡體中文）。
- 不做精細響應式設計（基本 mobile-friendly 即可，因是 H5）。
- 不做 E2E 自動化測試（前端冒煙測試人工執行）。
- 不做部署 / Docker / CI 配置。

## Edge cases

| 情境 | 預期行為 |
|---|---|
| 用戶名輸入「  」（全空白）| trim 後判定為空 → 校驗失敗，顯示用戶名格式錯誤文案 |
| 用戶名含非允許字符 | 校驗失敗，顯示用戶名格式錯誤文案 |
| 用戶名 21 字以上 | 校驗失敗 |
| localStorage 不可用（無痕模式 / 被禁用）| 點「登录」後 toast「无法保存登录状态」 |
| 後端 API 非 200 | 商品列表顯示「商品加载失败，请稍后重试」 |
| 重複插入相同 SKU | 違反 UNIQUE，IntegrityError |
| 訂單 `total_amount` 與 `unit_price * quantity` 不一致 | seed data 不允許，驗收條件 #6 阻擋 |
| `tracking_history` 為空陣列 | seed data 不允許，驗收條件 #10 阻擋 |
| `current_status` 與 history 末筆 status 不一致 | seed data 不允許，驗收條件 #11 阻擋 |

## Seed data 規格（最終 8 商品 + 5 訂單，簡體中文）

> **注**：以下為示意 + 規格，實作 `seed.py` 時定稿。

### 8 個商品（涵蓋不同價格區間，全部 stock > 0；image_url 用 Unsplash 公開圖）

| # | name | sku | stock | price | image_url（Unsplash photo id）|
|---|---|---|---|---|---|
| 1 | 蓝牙耳机·Pro | AUDIO-001 | 50 | 299.00 | 1505740420928-5e560c06d30e |
| 2 | 智能手表·X7 | WATCH-001 | 25 | 899.00 | 1523275335684-37898b6baf30 |
| 3 | 运动跑鞋·轻盈版 | SHOE-001 | 80 | 499.00 | 1542291026-7eec264c27ff |
| 4 | 机械键盘·87 键 | KB-001 | 100 | 459.00 | 1587829741301-dc798b83add3 |
| 5 | 无线鼠标·静音款 | MOUSE-001 | 200 | 99.00 | 1527864550417-7fd91fc51a46 |
| 6 | 便携充电宝·20000mAh | POWER-001 | 60 | 159.00 | 1609091839311-d5365f9ff1c5 |
| 7 | USB-C 数据线·三件装 | CABLE-001 | 500 | 39.90 | 1583394838336-acd977736f90 |
| 8 | 智能音箱·小白 | SPEAKER-001 | 15 | 599.00 | 1543512214-318c7553f230 |

完整 URL 模板：`https://images.unsplash.com/photo-{id}?w=400&h=400&fit=crop&auto=format`

### 5 筆訂單（≥ 3 用戶 × 涵蓋 ≥ 3 種物流狀態）

| # | username | product_sku | quantity | current_status |
|---|---|---|---|---|
| 1 | alex | AUDIO-001 | 2 | 已签收 |
| 2 | alex | KB-001 | 1 | 运输中 |
| 3 | tom | WATCH-001 | 1 | 已签收 |
| 4 | jerry | MOUSE-001 | 3 | 已发货 |
| 5 | jerry | CABLE-001 | 5 | 已签收 |

物流 history 範例（訂單 #1：alex 已送達的蓝牙耳机·Pro）：
```json
{
  "recipient": "张三",
  "address": "北京市朝阳区建国路88号",
  "phone": "13800138000",
  "tracking_no": "SF1234567890",
  "courier": "顺丰速运",
  "current_status": "已签收",
  "tracking_history": [
    {"timestamp": "2026-04-15T10:00:00", "status": "已下单", "location": "北京",         "description": "订单已创建"},
    {"timestamp": "2026-04-16T14:30:00", "status": "已发货", "location": "北京发货中心", "description": "已从仓库发出"},
    {"timestamp": "2026-04-17T09:15:00", "status": "运输中", "location": "上海中转中心", "description": "运输中"},
    {"timestamp": "2026-04-18T16:45:00", "status": "已签收", "location": "上海市浦东新区", "description": "已签收"}
  ]
}
```
