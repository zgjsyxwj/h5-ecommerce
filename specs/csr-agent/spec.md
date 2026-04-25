# 智能客服 Agent（Phase 2）

## Goal

为 Phase 1 的 H5 商城（`specs/h5-ecommerce-demo/`）接入智能客服 agent。用户在前端登录后，点击右下角浮动客服按钮 → 右侧面板展开 → 与 agent 流式对话。Agent 能：
- 查询当前登录用户的订单与物流时间线
- 回答商品信息（名称/SKU/价格/库存）
- 解释售后政策（退换货、退款时效、保修等）
- 应对品牌与常见 FAQ

> Phase 1 已就位：FastAPI + SQLite，8 商品 + 5 订单（含完整 logistics_info JSON）。Phase 2 不修改 Phase 1 的数据模型，只增量新增 agent 模块与聊天端点。

## Algorithm / 方法

**单 Agent + 4 个函数工具 + 内嵌 FAQ**：
- 模型：DeepSeek-V3（`deepseek-chat`），通过 agno `from agno.models.deepseek import DeepSeek` 接入。
- 工具：`lookup_orders` / `get_order_detail` / `get_product_info` / `list_products`，纯 SQLAlchemy 进程内查询，**不**走 HTTP 自调用。
- 知识库：~200 行 FAQ markdown（售后政策 + 品牌 FAQ）作为字符串拼接到 system instructions 内，**不**接向量库。
- 多轮：agno `SqliteDb(db_file="agent.db")` + `add_history_to_context=True, num_history_runs=10`。
- 流式：FastAPI `StreamingResponse(media_type="text/event-stream")` 包装 `agent.arun(..., stream=True, stream_events=True)`。

## Tech Stack

- 后端：agno >= 2.6 + openai >= 1.0（DeepSeek 走 OpenAI-compatible SDK）+ python-dotenv，集成进现有 FastAPI 单服务。
- 前端：现有 Vue 3 + Vite 项目下新增 `CsrPanel.vue` 组件 + `useChat.js` composable。
- 测试：pytest + FastAPI TestClient + **注入式 Agent stub**（chat 端点层测试不调真实 LLM，避免缓慢与烧 quota）。
- Storage：agno 用独立 `backend/agent.db`，与 Phase 1 的 `demo.db` 分开（避免污染电商 schema）。

## Public API

### 一、后端工具函数（agno tools，亦供 pytest 直测）

```python
# backend/app/agent/tools.py
def lookup_orders(username: str) -> list[dict]
def get_order_detail(order_id: int) -> dict
def get_product_info(query: str) -> list[dict]
def list_products() -> list[dict]
```

**订单摘要 dict 结构（lookup_orders 元素）—— 9 个键**：
```
order_id, product_name, product_sku, quantity,
unit_price, total_amount, current_status, tracking_no, courier
```

**订单详情 dict 结构（get_order_detail）—— 14 个键**：摘要 9 键 + `username, recipient, address, phone, tracking_history`。

**商品 dict 结构**：`id, name, sku, stock, price, image_url`（6 键）。

### 二、REST 端点

#### `GET /api/orders?username=<str>`
- 200：`[order_summary, ...]`
- 422：缺 `username` query
- 用户不存在：200 + `[]`（与工具行为一致）

#### `GET /api/orders/{order_id}`
- 200：`order_detail` (14 键)
- 404：`{"detail": "..."}`

#### `POST /api/chat`
- 请求 body：`{"message": str, "username": str, "session_id": str}`
- 返回：`Content-Type: text/event-stream`，按 SSE 事件协议流式输出
- 422：缺任一字段或为空字符串

### 三、SSE 事件协议

每个事件严格按 `event: <type>\ndata: <json>\n\n` 格式（双 `\n\n` 分隔）。

| event 类型 | data 结构 | 触发来源（agno event） |
|---|---|---|
| `token` | `{"text": "<增量文本>"}` | `RunContentEvent` |
| `tool` | `{"name": "<tool_name>", "phase": "start"\|"end"}` | `ToolCallStartedEvent` / `ToolCallCompletedEvent` |
| `done` | `{"session_id": "<sid>"}` | `RunCompletedEvent`，流结束 |
| `error` | `{"message": "<err>"}` | `RunErrorEvent` 或 endpoint 异常 |

### 四、前端组件

- 新增 `frontend/src/components/CsrPanel.vue`（右侧滑入面板）
- 新增 `frontend/src/composables/useChat.js`（`fetch` + `ReadableStream` 解析 SSE）
- 修改 `frontend/src/App.vue`（FAB 点击改为打开面板）

## 验收条件（Acceptance Criteria）

### 一、工具层（pytest 直测，**不**启动 LLM）

1. **lookup_orders 已知用户**：`lookup_orders("alex")` 返回 list 长度 **2**，含 `order_id ∈ {1, 2}`；每项是 dict，含上述 9 个键。
2. **lookup_orders 未知用户**：`lookup_orders("nobody")` 返回 `[]`。
3. **get_order_detail 存在**：`get_order_detail(1)` 返回 dict，`current_status == "已签收"`，`recipient == "张三"`，`tracking_no == "SF1234567890"`，`tracking_history` 长度 **4**。
4. **get_order_detail 不存在**：`get_order_detail(999)` 返回 `{"error": "order_not_found", "order_id": 999}`。
5. **get_product_info 按名称**：`get_product_info("蓝牙耳机")` 返回 list 长度 **1**，元素 `sku == "AUDIO-001"`、`price == "299.00"`。
6. **get_product_info 按 SKU**：`get_product_info("KB-001")` 返回 list 长度 **1**，元素 `name == "机械键盘·87 键"`。
7. **get_product_info 无匹配**：`get_product_info("不存在的商品")` 返回 `[]`。
8. **list_products 全量**：`list_products()` 返回 list 长度 **8**。

### 二、REST 端点层（FastAPI TestClient）

9. **GET /api/orders 有订单**：`?username=alex` → 200，body 是 list 长度 **2**，含 `order_id` 1 与 2。
10. **GET /api/orders 无订单**：`?username=nobody` → 200，body 是 `[]`。
11. **GET /api/orders 缺参**：无 `username` query → **422**。
12. **GET /api/orders/{id} 存在**：`/api/orders/1` → 200，body 是 dict，含 `tracking_history` 长度 **4**，`current_status == "已签收"`。
13. **GET /api/orders/{id} 不存在**：`/api/orders/999` → **404**，body 含 `detail`。

### 三、Chat 端点协议层（注入 stub Agent，**不**启动 LLM）

14. **POST /api/chat header**：合法请求 → status 200，`Content-Type` 起首为 `text/event-stream`。
15. **POST /api/chat 缺字段**：缺 `message` / `username` / `session_id` 任一（或为空字符串）→ **422**。
16. **SSE 事件序列**：stub agent 顺序 yield `[RunContentEvent("hi"), RunCompletedEvent(session_id="s1")]` → SSE 流顺序发出 `event: token\ndata: {"text":"hi"}\n\n` 与 `event: done\ndata: {"session_id":"s1"}\n\n`。
17. **SSE 工具事件**：stub agent yield `[ToolCallStartedEvent(tool=Tool(name="lookup_orders")), ToolCallCompletedEvent(...), RunCompletedEvent(...)]` → SSE 发出两个 `tool` event，`phase` 分别为 `"start"` / `"end"`，`name` 都是 `"lookup_orders"`。
18. **SSE 异常**：stub agent yield `[RunErrorEvent(content="api timeout")]` → SSE 发出一个 `error` event，HTTP 不报 500。

### 四、前端集成（手动冒烟，不在 pytest）

19. **点 FAB 开面板**：登录为 alex → 点右下 FAB → 右侧 360px 面板从 `translateX(100%)` 滑入，含「智能客服」标题、关闭按钮、消息列表、输入框、发送按钮。
20. **流式渲染**：发送「我的订单到哪了」→ 助手气泡逐字增长；至少看到一个「正在查询您的订单…」状态行；最终气泡提到 order_id 1 与 2 及其物流状态。
21. **Session 隔离**：另一 tab 登录为 tom 开新对话 → tom 看到的订单只有 tom 的（agno 按 user_id 隔离 history）。

---

## 待用户确认的歧义（Open Questions）

> 以下五个决策影响 spec 数字与 UX 行为，需在 Phase 2 计划前钉死。

### Q1：订单状态文字本地化 — 已通过 Phase 1 amendment 解决

**最终方案**：直接把 Phase 1 的 `TrackingStatus` 枚举值改成中文（`已下单` / `已发货` / `运输中` / `已签收`）。
- Pydantic 枚举的 Python 属性名仍是英文（`TrackingStatus.delivered`），保留代码可读性。
- JSON / DB / tool 输出统一用中文字符串。
- LLM 不需要做翻译，前端不需要做翻译，工具不需要做翻译。
- Phase 1 spec 同步更新（AC #12/13、JSON schema、seed 表）。
- 理由：演示项目，受众单一中文，分层抽象（机读 ID + 展示翻译）的成本超过收益。

### Q2：面板首屏 UX

用户第一次点开面板时，agent 是否主动发欢迎语？

- **(A) Recommended** — 不主动发，静态文案「您好，请描述您的问题」作为占位符；用户发第一条后 agent 才回复。**理由**：省 token、降首屏延迟、避免空对话历史污染。
- (B) 前端硬编码一条静态欢迎词（如「您好，我是 H5 商城智能客服，可帮您查询订单、商品与售后…」）。
- (C) 打开面板即调 LLM 生成个性化开场白（最重，最费 token）。

### Q3：工具调用可见性

SSE 流的 `tool` event 要不要展示给用户？

- **(A) Recommended** — 显示为小灰字状态行（如「正在查询您的订单…」），完成后消失或淡化。**理由**：流式空档（首 token 前 1–3 秒）让用户感知 agent 在做事，避免误以为卡死。
- (B) 完全隐藏，只看最终回复。
- (C) 显示但折叠（默认收起，可展开看调用名与耗时）。

### Q4：DeepSeek 报错 / 超时 UX

模型 API 失败（限流、5xx、超时）时，用户看到什么？

- **(A) Recommended** — SSE 发 `error` event，前端显示固定文案「服务暂时不可用，请稍后再试」+「重试」按钮（重发最后一条用户消息）。
- (B) 直接显示原始错误信息（暴露技术细节，不友好）。
- (C) 后端自动重试 1 次后再决定是否报错（多一层复杂度，可能放大延迟）。

### Q5：Session 生命周期

session_id 何时生成、何时清除？影响「多轮上下文」的范围。

- **(A) Recommended** — 面板首次打开时 `crypto.randomUUID()` 写入 `sessionStorage`，后续打开复用；关闭 tab 自动清除（`sessionStorage` 行为）。**理由**：对应「会话内多轮、无跨会话记忆」的选择；同 tab 内关闭再开面板继续同一会话。
- (B) 每次打开面板都生成新 session_id（每次都是「新对话」，前次历史不可见）。
- (C) 页面刷新就保留（用 `localStorage`，整个浏览器生命周期同一会话）。

---

## Non-goals

- ❌ 跨会话长期记忆（agno MemoryManager 不启用）
- ❌ 多 Agent / Team / Workflow（单 Agent 收敛所有能力）
- ❌ 向量库 RAG（FAQ 直接 prompt 注入）
- ❌ 真实鉴权（沿用 Phase 1 的 localStorage username）
- ❌ AgentOS 独立服务（集成进现有 FastAPI）
- ❌ WebSocket / 中断打断（纯 SSE 单向）
- ❌ 写操作（agent **只读**：不下单、不改地址、不发起退货）
- ❌ 语音 / 图片 / 文件输入
- ❌ 转人工
- ❌ 跨用户订单查询（agent 只能查传入 username 的订单）

## Edge cases

| 情境 | 预期行为 | 对应 AC |
|---|---|---|
| 用户名查无订单 | 工具返回 `[]`，agent 答「未查到您的订单」 | AC2 / AC10 |
| order_id 不存在 | 工具返回 error dict，agent 答「未找到该订单」 | AC4 / AC13 |
| 商品名模糊匹配多项 | 工具返回多项，agent 列出让用户选 | AC5 变体 |
| 用户问「全部商品」 | 触发 `list_products` | AC8 |
| /api/chat 缺字段 | 422 | AC15 |
| 同 session 多轮 | agno 自动注入历史，agent 记住上下文 | AC21 |
| DeepSeek API 5xx | SSE `error` event，前端显示重试（取决于 Q4） | Q4-A |
| 工具抛异常（DB 断） | agno 包成 `ToolCallErrorEvent`，agent fallback 或致歉 | Phase 6 verify |
| 用户问商城无关话题 | system prompt 约束婉拒，引导回客服话题 | (prompt 内置) |

---

## Phase 1 STOP

**请确认 Q1–Q5 的选择**（直接答「Q1-A, Q2-A, Q3-A, Q4-A, Q5-A」即可表示全部接受推荐答案；或逐个指定）。确认后进入 Phase 2 写 plan.md。
