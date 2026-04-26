# AI 编程联盟·h5商城 — 项目文档

> 第一期：商品展示 H5 + 用户登录 + 智能客服入口（占位）+ 订单数据预埋

---

## 一、业务概述

### 1.1 项目背景

本项目是 **AI 编程联盟** 出品的 H5 电商演示站点，用于演示「智能客服」SaaS 产品的应用场景。整个产品分两期推进：

| 阶段 | 范围 | 状态 |
|---|---|---|
| 第一期 | 商品展示 + 用户登录（前端 localStorage）+ 客服入口占位 + 后端订单数据预埋 | **已完成** |
| 第二期 | 智能客服对话功能，可基于第一期预埋的订单数据查询物流 | 规划中 |

### 1.2 目标用户

- **B 端决策者**：电商公司的产品总监、CTO、客服负责人，正在评估 AI 客服 SaaS 产品。
- **使用情境**：在销售演示、内部 demo、投资人路演场景中打开。
- **核心判断点**：8 秒内决定「这个团队的产品有品味且有工程能力」。

### 1.3 第一期用户故事

| 角色 | 行为 | 验收 |
|---|---|---|
| 未登录访客 | 打开站点查看商品 | 8 件商品（图片 / 名称 / 价格 / 剩余库存）正常展示 |
| 未登录访客 | 点击「智能客服」入口 | 弹 toast「智能客服功能即将上线，敬请期待」 |
| 未登录访客 | 在用户名输入框点一下 | 出现「演示账号」补全提示（alex / tom / jerry） |
| 用户 | 输入用户名后点「登录」 | 顶部状态变为「● 用户名」+「退出」 |
| 用户 | 刷新页面 | 登录状态保留 |
| 用户 | 点「退出」 | 回到未登录状态 |
| 用户 | 输入非法用户名（含特殊字符 / 超长 / 空白） | 弹错误 toast，登录失败 |
| 后端 | 启动应用 | 自动建表 + 种子写入 8 件商品 + 5 笔订单（含完整物流历史）|

### 1.4 第一期不做的事（Non-goals）

- **不做下单流程**：没有「立即购买」按钮，没有 `POST /api/orders`。
- **不做库存扣减**：`stock` 字段仅作展示用。
- **不做支付 / 物流真实对接**：物流数据是为第二期客服查询预埋的演示数据。
- **不做认证 / 密码 / 多因素**：用户名是纯字符串，后端不识别身份。
- **不做订单查询页**：「我的订单」页面留给第二期智能客服中实现。
- **不做客服对话**：客服按钮点击只显示 toast。

### 1.5 演示数据

#### 商品（8 件）

| 编号 | 名称 | SKU | 库存 | 单价 |
|---|---|---|---|---|
| 1 | 蓝牙耳机·Pro | AUDIO-001 | 50 | 299.00 |
| 2 | 智能手表·X7 | WATCH-001 | 25 | 899.00 |
| 3 | 运动跑鞋·轻盈版 | SHOE-001 | 80 | 499.00 |
| 4 | 机械键盘·87 键 | KB-001 | 100 | 459.00 |
| 5 | 无线鼠标·静音款 | MOUSE-001 | 200 | 99.00 |
| 6 | 便携充电宝·20000mAh | POWER-001 | 60 | 159.00 |
| 7 | USB-C 数据线·三件装 | CABLE-001 | 500 | 39.90 |
| 8 | 智能音箱·小白 | SPEAKER-001 | 15 | 599.00 |

#### 演示用户（3 个）

| 用户名 | 订单数 | 物流状态分布 |
|---|---|---|
| **alex** | 2 笔 | 1 笔已送达、1 笔运输中 |
| **tom** | 1 笔 | 已送达 |
| **jerry** | 2 笔 | 1 笔已发货、1 笔已送达 |

#### 订单（5 笔）

| # | 用户 | 商品 | 数量 | 总额 | 物流状态 |
|---|---|---|---|---|---|
| 1 | alex | 蓝牙耳机·Pro | 2 | 598.00 | 已签收 |
| 2 | alex | 机械键盘·87 键 | 1 | 459.00 | 运输中 |
| 3 | tom | 智能手表·X7 | 1 | 899.00 | 已签收 |
| 4 | jerry | 无线鼠标·静音款 | 3 | 297.00 | 已发货 |
| 5 | jerry | USB-C 数据线·三件装 | 5 | 199.50 | 已签收 |

每笔订单包含完整的物流追踪历史（tracking_history）：下单 → 已发货 → 运输中 → 已签收。

---

## 二、技术架构

### 2.1 系统总览

```
┌─────────────────────────────────────────────────────────────┐
│                      浏览器 (H5)                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Vue 3 单页应用 (App.vue)                 │   │
│  │   - 商品列表渲染（4/3/2 列响应式网格）                │   │
│  │   - 用户名登录（localStorage）+ 自动补全              │   │
│  │   - 客服浮动按钮 + Toast                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          │ fetch  GET /api/products          │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           ↓ JSON (CORS 已配)
┌─────────────────────────────────────────────────────────────┐
│             FastAPI 后端 (uvicorn :8001)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  路由: GET /api/products                             │   │
│  │  Pydantic 序列化 (ProductOut)                        │   │
│  │  Lifespan 启动钩子 → init_database()                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ↓ SQLAlchemy 2.x ORM                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SQLite (./demo.db)                                  │   │
│  │  - products (8 行)                                    │   │
│  │  - orders   (5 行 · logistics_info 为 JSON 字符串)    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 层 | 技术 | 版本 | 选型理由 |
|---|---|---|---|
| 前端框架 | Vue 3 | ^3.4 | 单页 SPA，组合式 API，无需路由库 |
| 构建工具 | Vite | ^5.4 | 启动 / HMR 极快，零配置 |
| 字体 | Hanken Grotesk + 系统中文栈 | — | 拉丁字母 Google Fonts，中文走 PingFang SC / HarmonyOS Sans SC |
| HTTP 客户端 | 原生 `fetch` | — | 单一接口无需引入额外库 |
| 后端框架 | FastAPI | ^0.110 | 异步、Pydantic 集成、自动 OpenAPI |
| 数据校验 | Pydantic v2 | ^2.6 | 物流 JSON 强约束 |
| ORM | SQLAlchemy | ^2.0 | 行业标准、新版 typed mapped_column |
| 数据库 | SQLite | Python 内置 | 演示零运维，文件级数据库 |
| Python | 3.12 | — | 性能与新语法 |
| 测试 | pytest + httpx | ^8 / ^0.27 | FastAPI TestClient 标准 |

### 2.3 项目结构

```
customer-service/
├── README.md                       ← 本文件
├── .impeccable.md                  ← 设计语言文档（前端美学方向）
├── backend/
│   ├── pyproject.toml              ← Python 项目配置
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 ← FastAPI 实例 + lifespan + CORS + 路由
│   │   ├── database.py             ← engine / Base / SessionLocal / get_db
│   │   ├── models.py               ← Product / Order SQLAlchemy ORM
│   │   ├── schemas.py              ← Pydantic 模型（含 LogisticsInfo 校验器）
│   │   └── seed.py                 ← 种子数据 + init_database()
│   ├── tests/
│   │   ├── conftest.py             ← in-memory SQLite fixture
│   │   ├── test_smoke.py
│   │   ├── test_products_api.py
│   │   ├── test_products_schema.py
│   │   ├── test_seed_products.py
│   │   ├── test_seed_orders.py
│   │   ├── test_logistics_info.py
│   │   └── test_seed_idempotency.py
│   └── demo.db                     ← SQLite 文件（运行后生成）
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html                  ← 入口 + Google Fonts 预连接
│   └── src/
│       ├── main.js                 ← createApp(App).mount('#app')
│       └── App.vue                 ← 单文件组件（页面全部逻辑 + 样式）
└── specs/h5-ecommerce-demo/
    ├── spec.md                     ← 需求规格（20 条验收条件 + Key Decisions）
    ├── plan.md                     ← 任务计划（15 个任务的 TDD 流程）
    └── verify.md                   ← 验收对应表（AC ↔ 测试映射）
```

### 2.4 数据模型

#### `products` 表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | 自增主键 |
| name | TEXT | NOT NULL | 商品名称 |
| sku | TEXT | NOT NULL, UNIQUE | 商品唯一编码 |
| stock | INTEGER | NOT NULL, CHECK >= 0 | 库存数量（仅展示，不扣减）|
| price | NUMERIC(10,2) | NOT NULL, CHECK > 0 | 单价（两位小数）|
| image_url | TEXT | NOT NULL | 商品配图 URL（Unsplash）|

#### `orders` 表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | 自增主键 |
| username | TEXT | NOT NULL | 下单用户名（无外键，直接字符串）|
| product_sku | TEXT | NOT NULL, FK → products.sku | 商品 SKU 引用 |
| product_name | TEXT | NOT NULL | 下单时的商品名称（**快照**）|
| unit_price | NUMERIC(10,2) | NOT NULL | 下单时的单价（**快照**）|
| quantity | INTEGER | NOT NULL, CHECK >= 1 | 数量 |
| total_amount | NUMERIC(10,2) | NOT NULL | 订单总额（= unit_price × quantity）|
| logistics_info | TEXT | NOT NULL | 物流信息 JSON 字符串（结构见下）|

> **快照设计**：`product_name` 与 `unit_price` 在创建订单时从 products 表拷贝，之后即使商品改名 / 调价也不会影响历史订单金额，符合电商基本约束。

#### `logistics_info` JSON 结构

```json
{
  "recipient": "张三",
  "address": "北京市朝阳区建国路88号",
  "phone": "13800138000",
  "tracking_no": "SF1234567890",
  "courier": "顺丰速运",
  "current_status": "已签收",
  "tracking_history": [
    {
      "timestamp": "2026-04-15T10:00:00",
      "status": "已下单",
      "location": "北京",
      "description": "订单已创建"
    },
    {
      "timestamp": "2026-04-18T16:45:00",
      "status": "已签收",
      "location": "上海市浦东新区",
      "description": "已签收"
    }
  ]
}
```

**字段约束（由 Pydantic `LogisticsInfo` 校验器强制）**：

- 7 个顶层字段全部必填，不允许多余字段。
- `tracking_history` 至少 1 条事件。
- 每条事件含 4 个字段：timestamp / status / location / description。
- `current_status` 必须等于 `tracking_history` 最后一条的 `status`。
- `status` 枚举值：`已下单` / `已发货` / `运输中` / `已签收`（Phase 2 amendment：枚举值统一中文，避免翻译层）。

### 2.5 API 接口

| 方法 | 路径 | 说明 | 响应 |
|---|---|---|---|
| GET | `/api/products` | 列出所有商品 | `200 OK` + `list[ProductOut]` |

**响应示例**：

```json
[
  {
    "id": 1,
    "name": "蓝牙耳机·Pro",
    "sku": "AUDIO-001",
    "stock": 50,
    "price": "299.00",
    "image_url": "https://images.unsplash.com/photo-1505740420928-..."
  }
]
```

> 第一期**仅有这 1 个接口**。订单相关接口（`GET /api/orders?username=xxx`、`GET /api/orders/{id}`）规划在第二期实现，本期只有数据，不暴露端点。

### 2.6 前后端交互

| 项 | 配置 |
|---|---|
| 前端开发地址 | `http://127.0.0.1:5173` |
| 后端 API 地址 | `http://127.0.0.1:8001` |
| CORS 允许来源 | `http://localhost:5173` 与 `http://127.0.0.1:5173` |
| 数据格式 | JSON |
| 价格序列化 | 字符串保留 2 位小数（避免浮点误差）|

### 2.7 数据初始化策略

- **何时初始化**：FastAPI `lifespan` 启动钩子触发 `init_database()`。
- **建表**：`Base.metadata.create_all(engine)`。
- **种子写入**：`seed_products(db)` + `seed_orders(db)`。
- **幂等性**：每个 seed 函数进入时先查 `count()`，若 > 0 直接 return。重启应用不会产生重复数据。
- **数据库文件**：`backend/demo.db`（SQLite 单文件，重启保留）。

### 2.8 登录与会话设计

- **后端无 session、无 token、无身份识别**：用户名只是订单的关联字段。
- **前端 localStorage 存登录态**：键名 `username`，值为字符串。
- **用户名校验规则**：
  - 长度 1–20
  - 字符集：`[a-zA-Z0-9 中文 _]`
  - 校验正则：`/^[a-zA-Z0-9一-龥_]{1,20}$/`
- **演示账号补全**：前端硬编码 `['alex', 'tom', 'jerry']`，输入框获焦或输入时弹下拉，前缀匹配过滤。

### 2.9 测试策略

| 维度 | 方式 | 数量 |
|---|---|---|
| 后端单元 + 集成 | pytest + FastAPI TestClient + in-memory SQLite | **16 个** |
| 数据库隔离 | `sqlite:///:memory:` + StaticPool（避免多线程见到不同 DB）| — |
| 前端 | 手动冒烟（不引入 E2E 工具）| 6 项 |

**16 个 pytest 测试**：

```
tests/test_smoke.py                 ← 冒烟测试（app 可导入）
tests/test_products_schema.py       ← SKU UNIQUE 约束
tests/test_products_api.py          ← 空列表 + 8 件商品 API
tests/test_seed_products.py         ← 种子商品数量 + 库存约束
tests/test_seed_orders.py           ← 5 笔订单 + 金额 + 快照
tests/test_logistics_info.py        ← 物流 JSON 结构（5 个）+ 状态多样性
tests/test_seed_idempotency.py      ← 重启不重复
```

运行：`cd backend && .venv/bin/pytest -q` → `16 passed`

### 2.10 前端设计语言

详见 [.impeccable.md](.impeccable.md)。摘要：

- **主题**：浅色，暖纸白底（B 端桌面情境）
- **字型**：Hanken Grotesk（Google Fonts）+ 系统中文栈
- **配色**：墨色三阶 + 唯一强调色「深森绿」`oklch(38% 0.085 152)`
- **细节**：髮丝线（hairline）取代阴影；不用 emoji 装饰；不用圆形 chat bubble；不用渐变文字
- **动效**：60ms stagger 入场、hover 700ms 图片缓慢放大、`prefers-reduced-motion` 友好

---

## 三、本地启动

### 3.0 前置要求

- **Python**：3.12（其他版本未测试，`pyproject.toml` 钉死 `>=3.12,<3.13`）
- **Node**：建议 18+（Vite 5 要求）
- **DeepSeek API Key**：访问 [https://platform.deepseek.com/](https://platform.deepseek.com/) 注册账号、创建 key

### 3.1 启动后端（首次）

```bash
cd backend

# 1) 建虚拟环境
python3.12 -m venv .venv

# 2) 安装依赖（含 agno、openai、python-dotenv 等）
.venv/bin/pip install -e ".[dev]"

# 3) 配置 DeepSeek API Key（智能客服必需）
cp .env.example .env
# 编辑 .env 文件，填入 DEEPSEEK_API_KEY=sk-xxxxxxxx

# 4) 启动开发服务器
.venv/bin/uvicorn app.main:app --reload --port 8001 --host 127.0.0.1
```

后续启动只需第 4 步。

启动后：
- API 根：`http://127.0.0.1:8001/`
- Swagger UI：`http://127.0.0.1:8001/docs`（可见 4 个端点：`/api/products`、`/api/orders`、`/api/orders/{order_id}`、`/api/chat`）

> **未配 `DEEPSEEK_API_KEY`** 时，`/api/products`、`/api/orders` 仍可用；只有 `/api/chat` 在第一次调用时报错。

### 3.2 启动前端

另开 terminal：

```bash
cd frontend
npm install         # 首次
npm run dev
```

打开 `http://127.0.0.1:5173/` 看到完整 H5 商城。

### 3.3 运行测试

```bash
cd backend
.venv/bin/pytest -q     # 36 passed
.venv/bin/pytest -v     # 详细列出每个测试
```

测试不调用真实 LLM（用 stub agent 注入），跑完只需约 0.1 秒。

### 3.4 端到端烟测（智能客服）

在前端页面 (`http://127.0.0.1:5173/`)：

1. **登录**：用户名输入框选 `alex`（也支持 `tom` / `jerry`），点「登录」
2. **打开客服**：点右下角浮动按钮 → 右侧滑入面板
3. **测试 4 大能力**：

| 问 | 期望行为 |
|---|---|
| 我的订单到哪了 | 灰字「正在调用 lookup_orders…」+ 流式回复列出 alex 的 2 单（运输中 + 已签收） |
| 订单 1 物流详情 | 调用 `get_order_detail`，给出 4 个物流时间节点 |
| 蓝牙耳机多少钱 | 调用 `get_product_info("蓝牙耳机")`，答 ¥299 |
| 7 天无理由怎么操作 | 引用 FAQ 内容回答（不调任何工具） |
| 怎么修改收货地址 | 引用 FAQ「发货前免费改」 |

4. **测试错误恢复**：临时把 `.env` 里的 `DEEPSEEK_API_KEY` 改成 `sk-invalid` 重启后端 → 再发消息 → 应看到「服务暂时不可用」+「重试」按钮（验证 spec Q4-A）
5. **测试 session 隔离**：关 tab 重开 → 历史消息消失（sessionStorage，验证 spec Q5-A）；同 tab 内关闭面板再打开 → 历史保留

### 3.5 重置演示数据

```bash
cd backend

# 重置电商数据（products + orders）
rm demo.db

# 重置客服对话历史（所有 session 清空）
rm agent.db

# 下次启动后端时 demo.db 会自动 seed；agent.db 会按需创建
```

---

## 四、第二期规划（草案，待立 spec）

### 4.1 范围

- **智能客服对话**：客服按钮从「占位 toast」升级为真实对话窗口。
- **物流查询能力**：客服可基于已登录的 `username` 检索其名下订单，并展示 `tracking_history` 时间线。
- **可能的后端工作**：
  - 新增 `GET /api/orders?username={username}` 列出某用户订单
  - 新增 `GET /api/orders/{id}` 查询单笔订单详情（含完整物流）
  - LLM 对话引擎接入（API key 配置 / Streaming 协议选型）
  - 可能需要 SSE 或 WebSocket
- **可能的前端工作**：
  - 客服对话面板（替代当前 toast）
  - 订单卡片组件 + 物流时间线组件

### 4.2 待决策事项（从 verify.md 灰色地带继承）

1. **客服如何识别当前用户**？通过 query 参数还是直接读 localStorage？
2. **物流时间戳是否带时区**？目前是 naive ISO8601，无 `+08:00` / `Z`。
3. **订单是否新增 `created_at` / `updated_at`**？
4. **`stock` 字段在客服场景的用途**？
5. **客服对话历史是否落库**？

这些问题在第二期立 spec 时统一拍板。

---

## 五、相关文档

| 文档 | 用途 |
|---|---|
| [specs/h5-ecommerce-demo/spec.md](specs/h5-ecommerce-demo/spec.md) | 第一期需求规格（20 条验收条件 + Key Decisions + Non-goals）|
| [specs/h5-ecommerce-demo/plan.md](specs/h5-ecommerce-demo/plan.md) | 第一期任务计划（15 个任务的 TDD 流程）|
| [specs/h5-ecommerce-demo/verify.md](specs/h5-ecommerce-demo/verify.md) | 验收条件 ↔ 测试用例对应表 + 灰色地带清单 |
| [.impeccable.md](.impeccable.md) | 前端设计语言（用户画像 / 视觉方向 / 配色 / 字体）|
