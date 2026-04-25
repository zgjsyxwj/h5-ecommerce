# Phase 6 — Verify Mapping

把 [spec.md](./spec.md) 的 20 條驗收條件逐條對應到測試 / 手動驗證手段。

最終測試成績：**16 passed**（後端全部自動）+ **6 條前端條件**改手動冒煙。

---

## 後端驗收條件（pytest 自動驗證）

| # | 驗收條件 | 對應測試 | 結果 |
|---|---|---|---|
| 1 | `GET /api/products` 回 200 + JSON list，每元素含 5 鍵 | [`test_should_return_eight_products_with_required_fields_via_api`](../../backend/tests/test_products_api.py) + [`test_should_return_empty_list_when_no_products`](../../backend/tests/test_products_api.py) | ✅ |
| 2 | products 共 8 筆 | [`test_should_have_eight_seed_products`](../../backend/tests/test_seed_products.py) | ✅ |
| 3 | 全部 stock > 0（無售罄概念） | [`test_should_have_all_products_with_positive_stock`](../../backend/tests/test_seed_products.py) | ✅ |
| 4 | SKU UNIQUE 約束 | [`test_should_raise_integrity_error_when_inserting_duplicate_sku`](../../backend/tests/test_products_schema.py) | ✅ |
| 5 | orders 共 5 筆，≥3 distinct username | [`test_should_have_five_seed_orders_with_at_least_three_distinct_users`](../../backend/tests/test_seed_orders.py) | ✅ |
| 6 | `total_amount == unit_price × quantity` | [`test_should_have_total_amount_equal_unit_price_times_quantity_for_all_orders`](../../backend/tests/test_seed_orders.py) | ✅ |
| 7 | `product_sku` 必存於 products | [`test_should_match_product_snapshot_at_order_time`](../../backend/tests/test_seed_orders.py)（同時驗證 #7 #8） | ✅ |
| 8 | `product_name` / `unit_price` 為 snapshot | 同上 | ✅ |
| 9 | logistics_info 含 7 個頂層欄位 | [`test_should_have_seven_top_level_fields_in_logistics_info`](../../backend/tests/test_logistics_info.py) | ✅ |
| 10 | tracking_history ≥ 1 筆，每筆 4 欄 | [`test_should_have_non_empty_tracking_history_with_four_fields_per_event`](../../backend/tests/test_logistics_info.py) | ✅ |
| 11 | current_status == history 末筆 status | [`test_should_match_current_status_with_last_history_event`](../../backend/tests/test_logistics_info.py) + Pydantic `model_validator` | ✅ |
| 12 | status ∈ {order_placed, shipped, in_transit, delivered} | [`test_should_use_only_valid_status_enum_values`](../../backend/tests/test_logistics_info.py) + Pydantic `TrackingStatus` enum | ✅ |
| 13 | 5 訂單涵蓋 ≥3 distinct current_status | [`test_should_cover_at_least_three_distinct_current_statuses_in_seed_orders`](../../backend/tests/test_logistics_info.py) | ✅ |
| 14 | seed 冪等（重啟不重複） | [`test_should_not_duplicate_seed_data_on_repeated_init`](../../backend/tests/test_seed_idempotency.py) | ✅ |

**14/14 自動覆蓋。**

額外 regression guards（Pydantic schema 校驗）：[`test_should_parse_logistics_info_with_valid_pydantic_schema_for_all_orders`](../../backend/tests/test_logistics_info.py) 從整體 schema 角度驗證 5 筆訂單 logistics_info 全可解析。

---

## 前端驗收條件（手動冒煙測試）

啟動方式：
1. 後端：`cd backend && .venv/bin/uvicorn app.main:app --port 8001`
2. 前端：`cd frontend && npm run dev`（默認 :5173）
3. 瀏覽器打開 `http://127.0.0.1:5173/`

| # | 驗收條件 | 驗證步驟 |
|---|---|---|
| 15 | 未登錄即可看 8 張商品 | 打開頁面，無需登錄即顯示 8 張卡片（蓝牙耳机·Pro / 智能手表·X7 / ...） |
| 16 | 登錄持久化 | 輸入 `alex` → 點「登录」→ 頂部變「欢迎，alex」→ F5 仍然「欢迎，alex」 |
| 17 | 退出 | 已登錄狀態下點「退出」→ 回到輸入框 + 「登录」按鈕狀態，localStorage `username` 被清 |
| 18 | 用戶名校驗 | 空字串 / `!@#` / 21 字母 → 各自顯示 toast「用户名长度需为 1-20 位，仅允许字母、数字、中文、下划线」 |
| 19 | 客服按鈕 + toast | 右下角浮動按鈕（無論登錄狀態）→ 點擊彈 toast「智能客服功能即将上线，敬请期待」，3 秒後消失 |
| 20 | API 失敗降級 | 把後端 uvicorn 停掉 → 刷新前端 → 顯示「商品加载失败，请稍后重试」 |

---

## Spec 灰色地帶（Verify 階段發現，留作後續決策）

跑完所有 task 才浮現以下 spec 沒明確定義的邊界：

1. **登錄狀態下的客服按鈕點擊行為是否傳遞 username？**
   - 第二期客服需要識別當前用戶。本期 toast 沒帶 username。第二期需確認入口怎麼把 username 傳給客服模塊（query param? localStorage 直接讀?）。

2. **物流 `timestamp` 是否需要時區？**
   - 目前用 naive ISO8601（`2026-04-15T10:00:00`），無時區後綴。第二期客服展示時間給用戶看，需確認是否加 `+08:00` 或 `Z`。

3. **logistics_info 在 SQLite 是 TEXT，無 JSON CHECK 約束**
   - Pydantic 在 application 層校驗，但 raw SQL 直接寫入可繞過。spec 沒要求 DB-level JSON schema 校驗，是有意為之。

4. **Order 沒有 created_at / updated_at**
   - 對訂單追蹤無用，但客服可能需要「下單時間」。第二期可能要加。

5. **`stock` 字段意義**
   - 本期僅展示，無扣減語義。第二期客服可能查「我這個訂單還能買多少」也用得到當前 stock。

6. **`/api/orders` endpoint**
   - 本期 spec 明訂第二期才做（Q11-A）。第二期需獨立 spec/plan。

7. **單元測試對「測試代碼本身」的健壯性**
   - 例如 conftest 的 `db_session` 使用 in-memory + StaticPool，這是測試實作細節，非 spec 約束。生產 SQLite 用文件，行為一致性靠 SQLAlchemy 抽象保證。

這些不是 bug，是 spec 演化空間。

---

## 最終專案結構

```
customer-service/
├── specs/h5-ecommerce-demo/
│   ├── spec.md
│   ├── plan.md
│   └── verify.md            ← 本檔案
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI + lifespan(init_database) + CORS
│   │   ├── database.py      # engine/Base/SessionLocal/get_db
│   │   ├── models.py        # Product / Order
│   │   ├── schemas.py       # ProductOut / TrackingStatus / TrackingEvent / LogisticsInfo
│   │   └── seed.py          # PRODUCT_SEED_DATA / ORDER_SEED_DATA / init_database
│   └── tests/
│       ├── conftest.py
│       ├── test_smoke.py
│       ├── test_products_api.py
│       ├── test_products_schema.py
│       ├── test_seed_products.py
│       ├── test_seed_orders.py
│       ├── test_logistics_info.py
│       └── test_seed_idempotency.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        └── App.vue
```

**測試成績**：`pytest -q` → 16 passed in 0.05s
