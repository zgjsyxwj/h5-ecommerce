# Plan — 智能客服 Agent

> 对应 [`spec.md`](./spec.md) 的 21 条 Acceptance Criteria，由简到繁拆成 12 个后端任务 + 3 个前端阶段。每个任务一次 Red → Green → (Refactor) → 可选 Regression Guard。

## 任务概览

| 阶段 | 任务 | 覆盖 AC | 依赖 |
|---|---|---|---|
| 工具层 | T1 list_products | AC8 | 无 |
| 工具层 | T2 get_product_info | AC5/6/7 | 无 |
| 工具层 | T3 lookup_orders | AC1/2 | 无 |
| 工具层 | T4 get_order_detail | AC3/4 | 无 |
| REST | T5 GET /api/orders | AC9/10/11 | T3 |
| REST | T6 GET /api/orders/{id} | AC12/13 | T4 |
| Chat | T7 POST /api/chat 协议骨架 | AC14/15 | 无 |
| Chat | T8 SSE token + done 映射 | AC16 | T7 |
| Chat | T9 SSE tool 事件映射 | AC17 | T8 |
| Chat | T10 SSE error 事件映射 | AC18 | T8 |
| 装配 | T11 真实 agent factory | — | T1-T4 |
| 接线 | T12 main.py 挂载 + dotenv | — | T5-T11 |
| 前端 | F1 useChat composable | — | T7-T10 |
| 前端 | F2 CsrPanel.vue | — | F1 |
| 前端 | F3 App.vue 集成 + 手动冒烟 | AC19/20/21 | F2 + T12 |

---

## 任务排序的理由

1. **工具层最先**：纯 SQLAlchemy，无 LLM 依赖，跑得最快。出问题最容易定位。
2. **T1 list_products 打头**：无入参，只验证「能拿到 8 件」，借此把测试基础设施（fixture、in-memory SQLite、seed）跑通，相当于 parking-fee 的「骨架任务」。
3. **T2-T4 顺序**：先无参（list_products），再带 query 的 get_product_info，再带 username 的 lookup_orders，最后查单条详情 get_order_detail。每步多一个维度。
4. **REST 在工具之后**：端点本质是「调工具 + 序列化 + HTTP 状态码」，先跑通工具再加 HTTP 层。
5. **Chat 端点在 REST 之后**：SSE 事件映射是新逻辑，需要一个稳定的 Agent stub 作为输入。
6. **T7 先做协议骨架（content-type + 422）再做事件映射（T8-10）**：让前端能尽早开始对接，事件类型可以一种一种加。
7. **T11 真实 agent 单独成任务**：与 SSE 协议解耦——Chat 端点用注入的 agent，T11 专注于「装配出一个能跑的 agent 实例」，不与协议测试纠缠。
8. **T12 接线放在最后**：所有零件就位才挂载，避免中间 OpenAPI 路由不稳定。
9. **前端整体放在最后**：依赖后端协议稳定，避免对着变动中的契约调试 SSE。

> **更深一层的派系考量**（Detroit 派 vs London 派、为什么不 TDD agno、为什么 spike 已消化风险）参见 [`journey.md`](./journey.md) 的「为什么底层向上」节。

---

## 后端任务详述

### T1 — list_products

- **覆盖**：AC8
- **Red**：`test_should_return_8_products_when_listing_all` — 调 `list_products()`，断言长度 == 8。预期红：函数不存在（`ImportError` 或 `NotImplementedError`）。
- **Green**：实现 `def list_products()`，`SessionLocal` 查全表，返回 dict 列表（含 6 键）。
- **Refactor**：评估是否抽 `_product_to_dict(p)` helper —— 只 1 处用，**不抽**。
- **Regression Guard**：暂无（其他工具会用同一辅助路径）。
- **Verify**：`pytest backend/tests/test_agent_tools.py::test_should_return_8_products_when_listing_all -v` → 1 passed

### T2 — get_product_info

- **覆盖**：AC5/6/7
- **Red**（一次只写 1 条）：`test_should_return_AUDIO_001_when_searching_by_chinese_name` — 调 `get_product_info("蓝牙耳机")`，断言长度 == 1 且 sku == "AUDIO-001"、price == "299.00"。
- **Green**：用 `or_(name LIKE %q%, sku LIKE %q%)` 一次性实现「按名 OR SKU」模糊匹配。
- **Refactor**：考虑抽 `_product_to_dict` —— 现在用 2 处（T1+T2），rule of three 不过，**不抽**；记入「等 T3 出现第三处再一起抽」的承诺。
- **Regression Guard 1**：`test_should_return_KB_001_when_searching_by_sku`（AC6）—— 同一份 Green 代码已覆盖，直接绿，钉住「按 SKU 也能搜」。
- **Regression Guard 2**：`test_should_return_empty_when_searching_unknown`（AC7）—— 同一份 Green 代码已覆盖，直接绿，钉住边界。
- **Verify**：3 passed

### T3 — lookup_orders

- **覆盖**：AC1/2
- **Red**：`test_should_return_two_orders_when_querying_alex` — 调 `lookup_orders("alex")`，断言长度 == 2，order_id 集合 == {1, 2}，每项是含 9 键的 dict。
- **Green**：`SessionLocal` 查 `Order.username == username`，逐行解析 `logistics_info` JSON，组装 9 键 dict。
- **Refactor**：考虑抽 `_parse_logistics(o)` helper —— 现在 1 处，**不抽**；预计 T4 会复用，到时候再一起。
- **Regression Guard**：`test_should_return_empty_when_user_has_no_orders`（AC2）—— 直接绿。
- **Verify**：2 passed

### T4 — get_order_detail

- **覆盖**：AC3/4
- **Red**：`test_should_return_full_detail_when_order_exists` — 调 `get_order_detail(1)`，断言 14 键齐全、`current_status == "已签收"`、`recipient == "张三"`、`tracking_no == "SF1234567890"`、`tracking_history` 长度 == 4。
- **Green**：`db.get(Order, order_id)`，None 则返 error dict，否则解析 JSON 组 14 键 dict。
- **Refactor**：T3 + T4 都解析 logistics JSON —— 三处出现（如果算 T3 摘要里的 9 键 + T4 的 14 键 + 此处的 history），**评估是否抽 `_logistics_payload(order_orm)` helper**。决定时机：看代码重复程度。预设倾向**不抽**——dict 形状不同（9 键 vs 14 键），抽出来反而要传字段子集。
- **Regression Guard**：`test_should_return_error_dict_when_order_id_unknown`（AC4）—— 直接绿。
- **Verify**：2 passed

### T5 — GET /api/orders

- **覆盖**：AC9/10/11
- **Red**：`test_should_return_alex_orders_when_get_orders_by_username` — TestClient `client.get("/api/orders?username=alex")` → 200，body 长度 2，order_id ∈ {1, 2}。
- **Green**：新建 `app/api/orders.py` 路由，`@router.get("/api/orders")` 带 `username: str = Query(...)`（注意：必填用 `Query(...)` 让 422 自动生效），内部调 `lookup_orders(username)`。在 main.py 临时 `include_router`。
- **Refactor**：暂无。
- **Regression Guard 1**：`test_should_return_empty_list_when_username_has_no_orders`（AC10）—— 直接绿。
- **Regression Guard 2**：`test_should_return_422_when_username_query_missing`（AC11）—— FastAPI 自动 422，直接绿，钉住对 Query 必填的依赖。
- **Verify**：3 passed

### T6 — GET /api/orders/{id}

- **覆盖**：AC12/13
- **Red**：`test_should_return_order_detail_when_get_by_id` — `client.get("/api/orders/1")` → 200，body 含 14 键，`tracking_history` 长度 4，`current_status == "delivered"`。
- **Green**：`@router.get("/api/orders/{order_id}")`，调 `get_order_detail(order_id)`；若返回 dict 含 `error` 键则 `raise HTTPException(404, ...)`，否则返回 dict。
- **Refactor**：暂无。
- **Regression Guard**：`test_should_return_404_when_order_id_unknown`（AC13）—— 直接绿。
- **Verify**：2 passed

### T7 — POST /api/chat 协议骨架

- **覆盖**：AC14/15
- **Red**：`test_should_return_event_stream_content_type_when_post_chat` — `client.post("/api/chat", json={"message": "hi", "username": "alex", "session_id": "s1"})` → 200，`response.headers["content-type"]` 起首 `"text/event-stream"`。
- **Green**：
  - 新建 `app/api/chat.py` 含 `ChatRequest` Pydantic 模型（3 字段，全 `min_length=1`）。
  - 路由返回 `StreamingResponse(media_type="text/event-stream")`，generator yield 单个 hardcoded `"event: done\ndata: {}\n\n"` 即可（最小绿）。
  - 测试中 patch `get_agent()` 返回一个空 stub（不调 LLM）。
- **Refactor**：考虑抽 `_emit(event_type, payload) -> str` helper —— 只 1 处，**不抽**；T8 起会反复用，到时再抽。
- **Regression Guard**：`test_should_return_422_when_chat_field_missing`（AC15）—— Pydantic 自动 422，钉住三字段必填。
- **Verify**：2 passed

### T8 — SSE token + done 映射

- **覆盖**：AC16
- **Red**：`test_should_emit_token_and_done_when_agent_yields_content_then_completed` — 让 stub agent 顺序 yield `[RunContentEvent(content="hi", run_id="r1", session_id="s1"), RunCompletedEvent(content="hi", run_id="r1", session_id="s1")]`；调 `/api/chat`；解析返回 SSE 流（按 `\n\n` 分块），断言两块依次为：
  ```
  event: token\ndata: {"text": "hi"}
  event: done\ndata: {"session_id": "s1"}
  ```
- **Green**：在 chat.py 的 generator 内 `async for ev in agent.arun(...stream=True, stream_events=True)`，按 `isinstance(ev, RunContentEvent)` / `isinstance(ev, RunCompletedEvent)` 分发。
- **Refactor**：现在 `_emit` helper 用了 2 次（token + done）—— 仍只 2 处，**继续不抽**；T9 加 tool 后变 4 处，到时一起评估。
- **Regression Guard**：暂无（多 token 拼接的行为留给真实 agent 端到端验证）。
- **Verify**：3 passed

### T9 — SSE tool 事件映射

- **覆盖**：AC17
- **Red**：`test_should_emit_tool_start_and_end_when_agent_calls_tool` — stub agent yield `[ToolCallStartedEvent(tool=Tool(tool_name="lookup_orders"), ...), ToolCallCompletedEvent(tool=Tool(tool_name="lookup_orders"), ...), RunCompletedEvent(...)]`；断言 SSE 流含两个 `event: tool` 块，phase 分别为 `"start"` / `"end"`，name 都为 `"lookup_orders"`。
- **Green**：在 generator 内加两个 `isinstance` 分支，提取 `ev.tool.tool_name`（实际字段名以 T8 实现期间 dump `dir(ev.tool)` 确认；spec 假设是 `tool_name`，但 agno 可能叫 `name` —— Red 失败时立刻调整）。
- **Refactor**：`_emit` 现在 4 处用，可能抽出来。但用法极简（`f"event: {t}\ndata: {json}\n\n"`），抽不抽差异不大。**仍倾向不抽**——把抽象延迟到 helper 长出第二个责任时。
- **Regression Guard**：暂无。
- **Verify**：4 passed

### T10 — SSE error 事件映射

- **覆盖**：AC18
- **Red**：`test_should_emit_error_when_agent_yields_run_error` — stub agent yield `[RunErrorEvent(content="api timeout", ...)]`；断言 SSE 流含一个 `event: error` 块，data 是 `{"message": "api timeout"}`，HTTP 状态仍为 200（不抛 500）。
- **Green**：在 generator 内加 `isinstance(ev, RunErrorEvent)` 分支，发完 error event 后 `return`。整个 generator 套 `try/except` 捕获 endpoint 自身异常发同样的 error event。
- **Refactor**：T8-T10 跑完，generator 的事件分发逻辑可能值得抽一个 `_event_to_sse(ev) -> str | None` helper。**评估**：5 个分支并列在 generator 体内还算可读；抽出去要传一堆参数（`session_id` 等）。**仍不抽**；如果 T11 装配真实 agent 时再发现需要复用，那时候抽。
- **Regression Guard**：暂无。
- **Verify**：5 passed

### T11 — 真实 agent factory

- **覆盖**：无具体 AC（构造性检查）
- **Red**：`test_should_build_agent_with_four_tools_and_faq_in_instructions` — 调 `from app.agent.agent import get_agent; a = get_agent()`，断言：
  - `isinstance(a, Agent)` （agno Agent）
  - `len(a.tools) == 4`，且工具名集合 == `{"lookup_orders", "get_order_detail", "get_product_info", "list_products"}`
  - `"<faq>" in a.instructions and "</faq>" in a.instructions`（FAQ 已注入）
  - `a.add_history_to_context is True`、`a.num_history_runs == 10`
- **Green**：实现 `app/agent/agent.py`：FAQ_MARKDOWN 注入 instructions，DeepSeek 模型，4 工具，SqliteDb("agent.db")，多轮配置。`get_agent()` 单例。
- **Refactor**：暂无。
- **Regression Guard**：无。
- **Verify**：1 passed

### T12 — main.py 接线

- **覆盖**：无具体 AC
- **Red/Green 一并**（接线任务）：
  - `main.py` 顶部 `from dotenv import load_dotenv; load_dotenv()`
  - `app.include_router(orders.router)` + `app.include_router(chat.router)`
  - 创建 `backend/.env` + `.env.example` + `.gitignore`（之前撤销过，本次重做）
- **Verify**：
  - `pytest backend/tests/ -v` → 全绿
  - `curl http://127.0.0.1:8001/openapi.json | jq '.paths | keys'` 含 `/api/orders`、`/api/orders/{order_id}`、`/api/chat`
- **Refactor**：无。

---

## 前端阶段

### F1 — useChat composable

- 文件：`frontend/src/composables/useChat.js`
- 实现：暴露 `messages` ref + `send(text, username, sessionId)` 方法。内部用 `fetch + ReadableStream + TextDecoderStream`，按 `\n\n` 切块，识别 `event: <type>` + `data: <json>`，分发到本地 reducer 更新 messages（user / assistant / tool-status / error 四种气泡类型）。
- 验证：在 Chrome devtools 里手测一次 `useChat().send("hi", "alex", "s1")`，确认 messages 数组按预期变化。

### F2 — CsrPanel.vue

- 文件：`frontend/src/components/CsrPanel.vue`
- 结构：右侧 360px 滑入面板（`translateX(100%) → 0`，260ms ease-out），含 Header（标题「智能客服」+ 关闭按钮）、消息列表（4 类气泡：user / assistant / tool-status 灰字 / error 红字+「重试」按钮）、底部 textarea + 发送按钮。
- 用 `useChat()` 驱动消息流。
- 暴露 `v-model:open` props。
- session_id：`sessionStorage.getItem("csr_session") ?? crypto.randomUUID()`，首次写回。

### F3 — App.vue 集成 + 手动冒烟

- 修改 `frontend/src/App.vue`：
  - `import CsrPanel from './components/CsrPanel.vue'`
  - 新增 `const panelOpen = ref(false)`
  - `handleCsrClick`：未登录 → toast 提示先登录；已登录 → `panelOpen.value = true`
  - 模板里挂 `<CsrPanel v-model:open="panelOpen" :username="username" :api-base="API_BASE" />`
- **冒烟测试清单（AC19/20/21）**：
  1. 登录为 alex → 点 FAB → 面板从右滑入
  2. 输入「我的订单到哪了」→ 看到「正在查询您的订单…」灰字状态行 → 流式回复列出 alex 的两单 + 物流状态（中文如「运输中」「已送达」，验证 Q1-A）
  3. 问「7 天无理由怎么操作」→ 引用 FAQ 内容回答
  4. 问「蓝牙耳机多少钱」→ 答 ¥299
  5. 关闭面板再打开 → 历史消息仍在（同 session）
  6. 关闭 tab 再打开 → 历史消息消失（sessionStorage 行为，验证 Q5-A）
  7. 临时把 DEEPSEEK_API_KEY 设成无效值 → 再发一条 → 显示「服务暂时不可用…」+ 重试按钮（验证 Q4-A）

---

## Phase 2 STOP

**请确认计划合理**——任务数（12 + 3）/ 顺序 / 测试粒度。确认后从 T1 开始 Phase 3 Red：我会先把 T1 的测试代码贴出来给您过目，您说「测试 OK」再写文件。

> 所有命名约定：测试函数 `test_should_<X>_when_<Y>`，body 用 `# Given / # When / # Then`，文件按 `tests/test_<area>.py` 分组。
