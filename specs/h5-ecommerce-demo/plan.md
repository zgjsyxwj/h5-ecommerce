# H5 商品展示與訂單預埋 — 實作計畫

把 [spec.md](./spec.md) 的 21 條驗收條件拆成 15 個 task，由簡到繁排序。後端 task 走嚴格 TDD（Red → Green → Refactor），前端 task 走「實作 + 手動冒煙」。

---

## 專案結構（最終樣貌）

```
customer-service/
├── specs/h5-ecommerce-demo/
│   ├── spec.md
│   └── plan.md
├── backend/
│   ├── pyproject.toml         # Python 3.12 + fastapi + sqlalchemy + pytest
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app + startup hook
│   │   ├── database.py        # engine / session / Base
│   │   ├── models.py          # Product / Order ORM
│   │   ├── schemas.py         # Pydantic（含 LogisticsInfo, TrackingEvent）
│   │   ├── api.py             # GET /api/products
│   │   └── seed.py            # 8 商品 + 5 訂單
│   └── tests/
│       ├── conftest.py        # in-memory SQLite fixture
│       └── test_*.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        └── api.js             # fetch wrapper
```

---

## 排序理由

- **Task 1** 先把工具鏈跑通（pytest + uvicorn 啟得起來），避免後面卡 setup。
- **Task 2-4** 先做 products，因為 orders 引用 products（FK 與 snapshot），products 必須先存在。
- **Task 5-7** 做 orders 主結構，但 logistics_info 暫用最簡 stub。
- **Task 8-9** 把 logistics_info 從 stub 升級成 Pydantic 校驗 + 多樣性。**這是本期最複雜的部分**，放後段一次處理避免反覆。
- **Task 10** seed 冪等放最後，因為前面的 seed 邏輯已成型。
- **Task 11** CORS 是後端最後一塊，為前端鋪路。
- **Task 12-15** 前端按「能看到 → 能交互 → 能容錯」順序：先渲染商品 → 加登錄 → 加客服按鈕 → 加錯誤處理。

---

## 後端 Task（TDD）

### Task 1：項目骨架 + 工具鏈打通

**目標**：FastAPI 空 app 跑起來，pytest 認到測試。

**動作**：
- 建 `backend/pyproject.toml`，依賴：`fastapi`、`uvicorn[standard]`、`sqlalchemy>=2.0`、`pytest`、`httpx`（給 TestClient）
- 建 `backend/app/main.py`：`app = FastAPI()`，無 endpoint
- 建 `backend/tests/test_smoke.py`：`def test_can_import_app(): from app.main import app; assert app`

**Verify**：
- `cd backend && pytest -q` → 1 passed
- `cd backend && uvicorn app.main:app` → 啟動無報錯

**對應驗收條件**：無（純 setup）

---

### Task 2：`GET /api/products` 回空列表

**Red**：`test_should_return_empty_list_when_no_products`
- Given：DB 中 products 表為空
- When：`client.get("/api/products")`
- Then：status 200，body == `[]`

**Green**：
- `app/database.py`：建 SQLAlchemy engine + Base + SessionLocal
- `app/models.py`：定義 `Product`（id/name/sku/stock/price，**先不加 unique**）
- `conftest.py`：fixture 給每個測試 in-memory engine + create_all + override `get_db`
- `app/api.py`：`GET /api/products` 回 `select(Product).all()` 結果

**Verify**：上述測試綠；驗收條件 #1 部分（API 結構）。

---

### Task 3：SKU UNIQUE 約束

**Red**：`test_should_raise_integrity_error_when_inserting_duplicate_sku`
- Given：插入 `Product(sku="X-001")` 成功
- When：再插入 `Product(sku="X-001")`
- Then：`pytest.raises(IntegrityError)`

**Green**：`Product.sku = Column(String, unique=True, nullable=False)`

**Refactor**：考察 `name` / `price` 是否也要 NOT NULL CHECK — spec 寫了，順手加（已是 SQL constraint，code 不動）。

**Verify**：驗收條件 #4。

---

### Task 4：Seed 8 商品（全部 stock > 0）

**Red**：`test_should_have_eight_seed_products`
- Given：執行 `seed.seed_products(db)`
- When：查 `db.query(Product).count()`
- Then：== 8

**Green**：`app/seed.py:seed_products()` 寫入 spec 定稿的 8 筆。

**Regression guards**：
- `test_should_have_all_products_with_positive_stock`（驗收條件 #3，本期無售罄概念）— 直接綠
- `test_should_return_eight_products_with_required_fields_via_api`（驗收條件 #1 完整版，含 5 個欄位）— 紅，要更新 endpoint 改查 DB 才綠

**Verify**：驗收條件 #1, #2, #3。

---

### Task 5：orders 表 + 5 筆 seed（≥3 用戶）

**Red**：`test_should_have_five_seed_orders_with_at_least_three_distinct_users`
- Given：seed_products + seed_orders
- When：查 orders count + distinct username
- Then：count == 5，distinct username 數 >= 3

**Green**：
- `app/models.py`：新增 `Order` model（id/username/product_sku/product_name/unit_price/quantity/total_amount/logistics_info）
  - `logistics_info` 用 `Column(Text, nullable=False)`，**本 task 暫存 `"{}"` 占位**
- `app/seed.py:seed_orders()`：寫入 5 筆，alice × 2 / bob × 1 / charlie × 2

**Verify**：驗收條件 #5。

---

### Task 6：訂單金額一致性 (`total_amount = unit_price × quantity`)

**Red**：`test_should_have_total_amount_equal_unit_price_times_quantity_for_all_orders`
- Given：5 筆 seed 訂單
- When：對每筆訂單計算 `unit_price × quantity`
- Then：每筆 == `total_amount`（Decimal 兩位小數比較）

**Green**：`seed_orders` 內計算 `total_amount = unit_price * quantity` 後寫入。

**Verify**：驗收條件 #6。

---

### Task 7：訂單 `product_sku` 引用 + `product_name` / `unit_price` 快照

**Red**：`test_should_match_product_snapshot_at_order_time`
- Given：seed_products + seed_orders
- When：對每筆訂單，從 products 查相同 sku
- Then：`order.product_name == product.name` 且 `order.unit_price == product.price` 且 `product` 存在

**Green**：`seed_orders` 內每筆訂單先查 products 拿 name/price 寫入 order（嚴格 snapshot 邏輯）。

**Verify**：驗收條件 #7, #8。

---

### Task 8：物流 JSON Pydantic 校驗（7 頂層 + history 非空 + 4 欄/event + 狀態枚舉 + `current_status` 一致）

**Red**：`test_should_parse_logistics_info_with_valid_pydantic_schema_for_all_orders`
- Given：5 筆 seed 訂單
- When：對每筆 `order.logistics_info` 用 `LogisticsInfo.model_validate_json(...)` 解析
- Then：解析成功，無 ValidationError

**Green**：
- `app/schemas.py`：定義 `TrackingStatus(str, Enum)` 含 4 值 + `TrackingEvent`（4 欄）+ `LogisticsInfo`（7 欄）
- `LogisticsInfo` 加 `model_validator(mode="after")` 強制 `current_status == tracking_history[-1].status` 且 `len(tracking_history) >= 1`
- `seed_orders` 改為構造 `LogisticsInfo` 物件 → `.model_dump_json()` 後寫入 `order.logistics_info`

**Regression guards（直接綠）**：
- `test_should_have_seven_top_level_fields`（明確列舉欄位名）
- `test_should_have_non_empty_tracking_history`
- `test_should_have_four_fields_per_tracking_event`
- `test_should_use_only_valid_status_enum_values`
- `test_should_match_current_status_with_last_history_entry`

**Refactor**：考察是否抽 `STATUS_TRANSITIONS` 之類常數 — 沒有業務需要（demo 不檢查狀態轉移合法性），不抽。

**Verify**：驗收條件 #9, #10, #11, #12。

---

### Task 9：5 筆訂單涵蓋 ≥3 種 `current_status`

**Red**：`test_should_cover_at_least_three_distinct_current_statuses_in_seed_orders`
- Given：5 筆 seed 訂單
- When：收集所有 `current_status`（從 logistics_info 解析出來）
- Then：distinct 數 >= 3

**Green**：調整 spec 中定稿的 5 筆訂單 status 分佈：`delivered / in_transit / delivered / shipped / delivered` —— 涵蓋 3 種狀態。

**Verify**：驗收條件 #13。

---

### Task 10：Seed 冪等（重啟不重複）

**Red**：`test_should_not_duplicate_seed_data_on_repeated_init`
- Given：執行 `init_db()`（建表 + seed），第一次後 products=8 / orders=5
- When：再執行一次 `init_db()`
- Then：products 仍 8 / orders 仍 5（不疊加）

**Green**：`seed_products` / `seed_orders` 進入時先 `if db.query(Product).count() > 0: return`。

**Verify**：驗收條件 #14。

---

### Task 11：CORS

**目標**：前端 dev server（`http://localhost:5173`）能訪問後端（`http://localhost:8000`）。

**Red**：跳過（CORS 屬中間件配置，TDD 不易測；改為手動驗證）。

**Green**：`app/main.py` 加 `CORSMiddleware`，allow_origins=`["http://localhost:5173"]`，allow_methods/headers=`["*"]`。

**Verify**：手動 — 前端 `fetch("/api/products")` 不報 CORS 錯誤（Task 12 完成後驗）。

---

## 前端 Task（實作 + 手動冒煙）

> 前端用 Vite 創建：`npm create vite@latest frontend -- --template vue`，安裝後 `npm install`、`npm run dev`。

### Task 12：Vue 3 骨架 + 商品列表

**動作**：
- `App.vue`：`onMounted` 內 `fetch('http://localhost:8000/api/products')` → 渲染卡片網格
- 每張卡片：商品名 / 價格 / 「剩余 N 件」
- 站名「Demo 商城」放頂部

**手動 Verify**（驗收條件 #15）：
- 後端開著的情況下，瀏覽器打開 `http://localhost:5173`
- 看到 8 張卡片，每張顯示商品名 / 價格 / 剩餘庫存

---

### Task 13：登錄表單 + localStorage 持久化 + 用戶名校驗

**動作**：
- `App.vue` 頂部加登錄區，狀態變數 `username = ref(localStorage.getItem('username') || '')`
- 未登錄：顯示 `<input placeholder="请输入用户名">` + `<button>登录</button>`
- 已登錄：顯示「欢迎，{username}」+「退出」按鈕
- 點「登录」：
  - 校驗 username：`/^[a-zA-Z0-9一-龥_]{1,20}$/`
  - 不合法 → toast「用户名长度需为 1-20 位，仅允许字母、数字、中文、下划线」
  - 嘗試 `localStorage.setItem('username', value)` → catch 例外 toast「无法保存登录状态，请检查浏览器设置」
- 點「退出」：`localStorage.removeItem('username')` + reset

**手動 Verify**（驗收條件 #16, #17, #18）：
- 輸入 `alice` → 登錄成功 → F5 仍登錄
- 點「退出」→ 回到未登錄
- 輸入空字串 / `!@#` / 21 字 → 各自彈錯誤 toast，登錄失敗

---

### Task 14：客服浮動按鈕 + toast（驗收條件 #19）

**動作**：
- `App.vue` 加 `<button class="csr-fab">客服</button>`，CSS `position:fixed; bottom:20px; right:20px; ...`
- 點擊：顯示 toast「智能客服功能即将上线，敬请期待」，3 秒後消失（用 `setTimeout`）
- toast 共用 Task 13 的 toast 組件 / 函數

**手動 Verify**（驗收條件 #19）：
- 登錄 / 未登錄狀態下，按鈕都可見
- 點擊彈 toast，3 秒消失

---

### Task 15：API 失敗降級

**動作**：
- `App.vue` 中 `fetch` 包 `try/catch`，失敗則設 `loadError = true`
- 商品列表區域：`v-if="loadError"` 顯示「商品加载失败，请稍后重试」

**手動 Verify**（驗收條件 #20）：
- 把後端 `uvicorn` 停掉，刷新前端 → 看到失敗文案

---

## 不在計畫內（明確排除）

- **E2E 自動化**：前端 4 個 task 純人工驗證，不引入 Playwright/Cypress。
- **CI/Lint/Format 配置**：demo 不需要。
- **Docker / 部署**：不做。
- **第二期客服 API**：spec Non-goals 明訂。

---

## Phase 3-5 流程提醒

逐 task 進行：
1. **Red**：寫 1 個 fail 測試 → `pytest -q` 確認紅 → STOP，等 review。
2. **Green**：最小程式 → 跑全部測試綠 → STOP，等 review。
3. **Refactor**：默認「不動」；若有具體 smell 才動，說明理由 → STOP，等 review。

前端 task 沒有 Red，但每個 task 完成後 STOP，等用戶手動驗證。
