# 智能客服 Agent — SDD + TDD 实施流程纪录

> 本文档完整记录用 SDD + TDD 工作流（参见 [`/Users/sid/sdd-tdd-workflow.md`](/Users/sid/sdd-tdd-workflow.md)）实施 Phase 2 智能客服 agent 的全过程。每一步的决策、理由、测试顺序的战略考量、为什么不重构、踩到的坑，都在这里。
>
> 教学目的：示范 SDD + TDD 在「带 LLM/外部依赖的真实项目」中如何落地——不仅是简单的纯函数计算（参考 parking-fee 例子），还包括 SQLAlchemy 数据层、FastAPI 端点、SSE 流式协议、Vue 前端等多层。

---

## 为什么选这个题目

题目：给 Phase 1 的 H5 商城接入「智能客服 agent」（agno + DeepSeek-V3）。

选这个题目的考虑：
- **真实场景**：电商客服几乎人人见过，不需要专业背景就能验证 agent 的回答合不合理。
- **多层架构**：纯 SQLAlchemy 工具层、HTTP REST 层、SSE 流式协议层、前端 UI 层——每一层都能演示「一个测试驱动一个行为」。
- **天然的歧义点**：状态枚举本地化、首屏 UX、错误处理⋯多个决策点适合演示「Spec 阶段如何把模糊语言钉死成具体决策」。
- **TDD + LLM 的难点**：模型调用慢、不确定、烧 quota——如何用「stub Agent + 注入 SSE 事件」避免在端点层测试时调真实模型，是个值得示范的工程难题。

---

## Phase 1 — Specify

产出：[`spec.md`](./spec.md)

### Spec 写完后浮现的 5 个歧义

写 spec 最重要的不是「把功能写全」，而是**把模糊的自然语言钉成具体决策**。初稿写完后，识别出 5 个用户必须拍板的歧义点：

| # | 议题 | 推荐答案 | 理由 |
|---|---|---|---|
| Q1 | 订单状态文字本地化 | 工具返回英文枚举，LLM 翻译 | 保留机读价值（可比较、可分支） |
| Q2 | 首屏 UX | 不主动发欢迎语 | 省 token、降首屏延迟 |
| Q3 | 工具调用可见性 | 显示为小灰字状态行 | 流式空档让用户感知 agent 在做事 |
| Q4 | 模型报错 UX | 固定文案 + 重试按钮 | 不暴露技术细节 |
| Q5 | session 生命周期 | sessionStorage（关 tab 清） | 对应「会话内多轮、无跨会话记忆」 |

**用户回答**：「全部 A」。一句话锁定 5 个决策。

### 中途的 pivot：Q1 重新讨论

锁完 Q1-A 后，用户接着追问：「有必要翻译吗？前端应该用不到状态吧？」

这是一个**很好的反思**。重新审视 Q1：
- 用户看到的中文文字来自 **LLM 的回复**，不是来自 tool 输出。
- Tool 返回 `"in_transit"` 给 agent → agent 在生成回复时自然写「运输中」（DeepSeek-V3 这种通用模型完全掌握电商常用词汇）。
- 前端只渲染 LLM 文本，**确实不会直接看到状态枚举**。

所以 Q1 本质是 tool 的边界设计，不是 UX 决策。

接着用户进一步说：「理论上，初始化数据中直接保存中文就行了。」

这是更深一层的设计观察：**与其在工具层用英文枚举 + 在 LLM 层翻译，不如让数据层直接是中文，整条链路无翻译**。

提出两种走法：
- **A**：改 Phase 1 的 `TrackingStatus` 枚举为中文值，整条链路统一中文。Q1 直接消失。
- **B**：保持 Phase 1 不动，让 LLM 自动翻译。零额外工作但留下「机读 ID + 展示翻译」的隐性约定。

用户最终选 **A**：「我们只是演示，不需要那么严谨」。这也是 demo 项目的合理选择——**抽象层的成本只在多团队/多语言/外部对接时才回本**，在固定中文受众的演示项目里，分层翻译是过度设计。

### 教学要点：Spec 阶段最重要的纪律

1. **歧义必须显式暴露**。看到模糊语言（「合理的」「合适的」「正确的」）就要追问「具体是什么数字/什么行为？」。这次 5 个 Q 全部都是这种「钉数字」的过程。
2. **Spec 是活文档**。中途 Q1 重新讨论后，spec.md 的 Q1 段落和 AC3、AC12 的字面值都要同步更新。**不更新就是 spec drift**，未来的 reader（包括将来的自己）会被误导。
3. **Pivot 的成本要估清**。从 B 切到 A 需要改 Phase 1 的 schemas.py + seed.py + spec.md。看起来 demo 项目「为了优雅改 Phase 1」是件小事，但若已经 ship 给真实用户，会议要开很久。这次因为是在自己单机上 demo，1 分钟决策就能切。

---

## Phase 1 Amendment — 把英文枚举改成中文

走 A 之后，Phase 1 的改动：

### 改了什么

| 文件 | 改动 |
|---|---|
| `backend/app/schemas.py` | `TrackingStatus` 枚举的 4 个值从英文换成中文（Python 属性名仍是英文：`TrackingStatus.delivered.value == "已签收"`） |
| `backend/app/seed.py` | 5 个 `current_status` + ~17 个 `tracking_history.status` 全部从英文换成中文，使用 `Edit` 工具的 `replace_all=true` 批量替换 |
| `specs/h5-ecommerce-demo/spec.md` | JSON schema 描述、AC #12/13、订单表、示例 logistics JSON 同步更新 |

### 关键决策

**Python 属性名保留英文**（`TrackingStatus.delivered`），只改字符串值（`"已签收"`）。理由：
- 代码里 `status == TrackingStatus.delivered` 这种判断仍然好读
- IDE 自动补全友好
- 只有「序列化到 JSON / DB / API」的边界呈现中文

### 跑测试验证

改完直接 `pytest -q`：**16 passed in 0.06s**。

为什么所有测试都没炸？看 `test_logistics_info.py`：

```python
valid_statuses = {s.value for s in TrackingStatus}
```

测试断言 `info["current_status"] in valid_statuses`，**枚举值变了，集合也跟着变**——这就是「测试断言绑行为不绑实现细节」的好处。如果当初测试写死了 `assert status == "delivered"`，这次重构就会全炸。

### 教学要点：测试与重构的关系

> **测试应该让重构变安全，而不是让重构变麻烦。**

写测试时永远问：「这个断言绑的是 spec 里说的『行为』，还是绑的是当前实现的『偶然形态』？」

Phase 1 测试用 `{s.value for s in TrackingStatus}` 而不是写死 `"delivered"`，正是绑行为不绑实现的体现。这个细节让 Phase 1 amendment 在零额外测试改动的情况下完成。

### Commit 划分

为了教学清晰，把这次改动拆成 2 个 commit：
1. `refactor: switch TrackingStatus enum from English to Chinese values` — 纯 Phase 1 改动
2. `docs(csr-agent): add Phase 2 spec and plan` — 纯 Phase 2 文档

**为什么不一锅炖？** 一个 commit 干一件事是 git 历史的基本卫生。reviewer 只想看「枚举为什么改」时，不需要被 Phase 2 的 600 行 spec 淹没。

---

## Phase 2 — Plan

产出：[`plan.md`](./plan.md)

### 把 21 AC 拆成 12 个后端任务 + 3 个前端阶段

| 阶段 | 任务数 | 覆盖 AC |
|---|---|---|
| 工具层 | T1-T4（4 个） | AC1-8 |
| REST | T5-T6（2 个） | AC9-13 |
| Chat 协议 | T7-T10（4 个） | AC14-18 |
| 装配 | T11（1 个） | — |
| 接线 | T12（1 个） | — |
| 前端 | F1-F3（3 个阶段） | AC19-21（手动） |

### 排序的战略考量

排序的核心原则是**让每一步都站在前一步的绿基础上前进，依赖关系最少的最先做**。

1. **工具层最先**：纯 SQLAlchemy，无 LLM 依赖，跑得最快。如果 T1 出错，问题一定在 fixture/SessionLocal 注入这种基础设施层面，方便定位。
2. **T1 list_products 打头**：无入参，最简单，相当于 parking-fee 的「骨架任务」——借此**把测试基础设施跑通**（fixture、in-memory SQLite、seed），后续任务直接复用。
3. **T2-T4 顺序**：先无参（list_products），再带 query 的 `get_product_info`，再带 username 的 `lookup_orders`，最后查单条详情 `get_order_detail`。**每步多一个维度**。
4. **REST 在工具之后**：HTTP 层只是「调工具 + 序列化 + 状态码」，先跑通工具再加 HTTP 装饰。
5. **Chat 端点在 REST 之后**：SSE 事件映射是新逻辑，需要稳定的 Agent stub 作为输入。Stub 比真实 agent 更可控，符合 TDD 的「快、稳、确定」。
6. **T11 真实 agent 单独成任务**：与 SSE 协议解耦——Chat 端点用注入的 stub agent，T11 只关注「能不能装出一个工具齐全、prompt 正确的 Agent 实例」，**不与协议测试纠缠**。
7. **T12 接线放最后**：所有零件就位才挂载，避免中间路由不稳定。
8. **前端整体放最后**：依赖后端协议稳定，**避免对着变动中的契约调试 SSE**。

### 教学要点：任务排序就是依赖图拓扑

每一个任务的 verify 必须能独立通过——不能「等下个任务做完才验证得了」。这就是为什么 chat 端点 (T7-T10) 和真实 agent (T11) 必须解耦的原因：用 stub agent 让 T7-T10 自给自足，否则就会变成「Phase 3 直到 T11 才有第一个绿」。

### 教学要点：为什么底层向上（Detroit 派）而不是顶层向下（London 派）？

> 上面 8 条排序理由全是「这次怎么做」的判断，但**为什么这次的判断长这样**？这是 TDD 派系之争——任何多层架构项目都绕不开。

**两种 TDD 流派**：

| 流派 | 别名 | 起点 | 风格 |
|---|---|---|---|
| **Detroit / Chicago / Classical** | 底层向上 | 从最底层数据/计算单元开始 | state-based 测试，少 mock，真实协作 |
| **London / Mockist** | 顶层向下 | 从用户行为/最外层端点开始 | behavior-based 测试，重度 mock 协作者 |

如果按 London 派开局，T1 就该是「用户发一句话给 agent，agent 回复一段话」端到端测试，agno、tools、DB 全 mock。

**这次为什么不走 London？**

| 判断 | 理由 |
|---|---|
| ✅ Spec 已写完 21 条 AC | 顶层向下的最大价值是「边写边发现接口形状」。我们 spec 阶段已经把每层契约钉死，**TDD 阶段不需要再用 mock 帮忙发现**。 |
| ✅ agno 是成熟依赖 | TDD 的目标是验证**自己写的代码**。「agent 能不能正确调用 tool」是 agno 的责任，不是我们的责任，**没必要给依赖写测试**。 |
| ✅ 风险已通过 spike 消化 | SSE 协议是真实风险点（agno 事件类名不熟）。但开 session 时已经跑过 probe 脚本列出 35 个事件类名 —— **风险被 spike 提前消化**，TDD 阶段不需要再扛这个不确定性。 |
| ✅ Tool 是多处复用的契约 | `lookup_orders` 同时被 agent 和 `/api/orders` 端点调用。**先把契约钉死，两个上层消费者都能放心依赖**。如果先做端点，会发现「等 tool 出来才知道我该传什么参数」。 |

**London 派的优势在哪？**

如果换一个项目：spec 模糊、依赖陌生、用户行为不确定 —— 那么 London 更合适。强制从「用户能感知到什么」倒推接口，避免做出一堆「完美但没人用」的零件。

**这次走 Detroit 的代价**：

理论上有「建好了 tool 才发现 agent 用不到」的风险。但 spec 把工具签名钉死了，agent 怎么调用是 prompt 的事 —— 对的工具能让差的 prompt 用，差的工具会让对的 prompt 也卡。**先把契约做对**。

**怎么判断该选哪派？** 一句话决策：
- spec 模糊/接口未知/依赖陌生 → London（用 mock 边做边定形）
- spec 完整/依赖成熟/契约清晰 → Detroit（用真实组件搭厚墙）

> **教学陷阱**：很多 TDD 入门书默认 London 风格，结果学习者在「契约清晰」的项目里也被迫 mock 每个协作者，写出比生产代码还复杂的测试结构。**派系是工具，不是教条**。

---

## Task 1 — list_products

**覆盖 AC**：AC8（`list_products()` 返回 list 长度 8）
**状态**：✅ 完成（Red → Green → 不重构）

### Red 提案

新建 `backend/tests/test_agent_tools.py`：

```python
import pytest
from sqlalchemy.orm import sessionmaker

from app.agent.tools import list_products
from app.seed import seed_products


@pytest.fixture
def tools_session(db_session, monkeypatch):
    """Bind app.agent.tools.SessionLocal to the test in-memory engine."""
    TestSessionLocal = sessionmaker(
        bind=db_session.get_bind(), autoflush=False, expire_on_commit=False
    )
    monkeypatch.setattr("app.agent.tools.SessionLocal", TestSessionLocal)
    return db_session


def test_should_return_8_products_when_listing_all(tools_session):
    # Given
    seed_products(tools_session)

    # When
    result = list_products()

    # Then
    assert len(result) == 8
    assert all({"id", "name", "sku", "stock", "price", "image_url"} <= p.keys() for p in result)
```

### 教学要点 1：为什么需要 `tools_session` fixture？

工具用 `SessionLocal()` 直连真实 `demo.db`：

```python
# tools.py（绿后会写成这样）
def list_products() -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(Product)).all()
        ...
```

但测试要用内存 SQLite（`sqlite:///:memory:`）。

如何让测试时 `SessionLocal()` 返回的是绑定到测试引擎的 session？

**方案对比**：

| 方案 | 优点 | 缺点 |
|---|---|---|
| (A) 用 monkeypatch 在测试时替换 `app.agent.tools.SessionLocal` | 生产代码零侵入，工具签名干净 | 需要在 fixture 里写 monkeypatch ceremony |
| (B) 改 tool 签名为 `def list_products(db: Session = None)` 之类 | 测试不需要 monkeypatch | 工具签名暴露了实现细节，agno 注册工具时要传 schema 也变复杂 |
| (C) 整个换成 SQLAlchemy `scoped_session` + 显式上下文管理 | 工业级解 | 远超 demo 复杂度 |

**选 (A)**。理由：**演示项目下，让测试承担一点 ceremony 比让生产代码长出依赖注入更划算**。这一条与「我们只是演示，不需要那么严谨」一脉相承。

注意 `monkeypatch.setattr("app.agent.tools.SessionLocal", ...)` 要 patch 在**导入位置**而非源位置——tools.py 里 `from app.database import SessionLocal` 之后，tools 模块自己持有了一个名为 `SessionLocal` 的引用。patch 源位置（`app.database.SessionLocal`）对 tools 不起作用，因为它的引用早就拿好了。

这个细节是 Python `import` 语义的常见坑，值得记下。

### 教学要点 2：为什么断言「长度 == 8」+「键集合包含 6 字段」是同一个 behavior？

AC8 字面只要求「返回 list 长度 8」。那是不是只断言 `len == 8` 就够了？

**反例**：Green 可以写成 `return [{}] * 8`——长度对，键集合空，断言通过。这是「钻空子」式的最小绿，**没有真正实现行为**。

下一步会拿到一个空 dict 的列表，T2/T3 测试很快就会发现，但这中间会有一段 false-green 时间。更糟的是这种 fake 实现会留在代码里，等下个 Red 来才被推翻——这违反「Green 是最简但**真实**的实现」原则。

加上「键集合包含 6 字段」的断言，逼 Green 真的去查 DB。两个断言**共同定义同一个 behavior**：「能从 DB 拿出 8 件、每件至少含 6 个字段」。

> **TDD 纪律的精确表述**：「一个测试一个 behavior」，不是「一个测试一个断言」。一个 behavior 可能需要多个断言协同钉住。

### 教学要点 3：什么叫「红得正大光明」？

Red 应该失败，但**失败原因要正确**。预期 Red：

```
ImportError: No module named 'app.agent'
```

这是「行为缺失」型失败——`list_products` 函数压根不存在。

**反面例子**：如果失败是 `pytest fixture 'tools_session' not found`，那就是 fixture 配错；`AssertionError: 'TestSessionLocal' is not callable` 是 monkeypatch 写错路径——这些都是「**setup 错**」而非「**行为缺失**」。setup 错的时候不能进 Green，必须先把 fixture 修对，让 Red 红在「行为缺失」上。

**判断方法**：看错误信息是否指向你想驱动的那个新行为。如果指向，红得正当；如果指向 fixture/import/拼写，红得不正当，先修 setup。

### Red 验证结果

写完测试后跑 pytest：

```
tests/test_agent_tools.py::test_should_return_8_products_when_listing_all
ModuleNotFoundError: No module named 'app.agent'
```

**红得正大光明** ✅ —— 错误指向「`app.agent` 模块不存在」，正是行为缺失。如果错误是「fixture 'tools_session' not found」就要回头修 fixture。

### Green 实现

新建 2 个文件：

`backend/app/agent/__init__.py`（空）

`backend/app/agent/tools.py`：
```python
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Product


def list_products() -> list[dict]:
    """列出商城全部在售商品。"""
    with SessionLocal() as db:
        rows = db.scalars(select(Product)).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "stock": p.stock,
                "price": str(p.price),
                "image_url": p.image_url,
            }
            for p in rows
        ]
```

跑 pytest：`tests/test_agent_tools.py::test_should_return_8_products_when_listing_all PASSED`，全套 17/17 绿。

### 教学要点 4：「最小绿」不等于「fake 绿」

Green 严格按 TDD 原则应该是「能让测试通过的最小代码」。最小是不是 `return [{"id": 1, ...}] * 8`？

**不是**。这种 fake 实现违反了「真实最小绿」原则：
- 如果 fake 能通过 T1 测试，它**也违反了断言原则**——断言不够严格才让 fake 过关。但加严断言（要求所有 6 个键都齐）后，fake 实现要写 8 行硬编码 dict 反而比真实查询代码更长更违和。
- Fake 解会留在代码里，等到下个 Red 才被推翻 —— **中间经过一段已知错误的状态**，这是 TDD 应该避免的。

正确理解：「最小」= **最少的概念抽象**，不是「最少的字符」。这次的 Green 是「**只**做一次 SELECT、组 dict、返回列表」—— 没加缓存、没加错误处理、没加 logger、没加 docstring 给 LLM 用 —— 那些都是未来 task 的事。

### Refactor 决策：不动

考虑过：抽一个 `_product_to_dict(p)` helper。

**拒绝理由**：
- 现在只用 1 处，rule of three 远未达到
- 还**预测**不到 T2 (`get_product_info`) 的 dict shape 是否真的一样（可能要带 match rank、relevance 之类的字段）
- **预测式抽象** = TDD 反模式 —— 抽错了比不抽更糟（重命名成本高于复用收益）

**承诺**：T2 出现第 2 处后再评估；**真**出现 3 处一致才抽。

### 教学要点 5：Refactor 的默认答案是「不动」

Kent Beck 原始 TDD 描述里，Refactor 是 **第三步**，但比例上应该最少。**4 次 refactor 阶段中至少 3 次都该是「评估 → 决定不动」**。

为什么不动？因为：
- 还没出现重复（rule of three）
- 抽出去的 helper 名字暂时取不准（因为还不知道未来用法）
- 抽出去的接口暂时定不死（因为还不知道下一个 caller 会传什么）

**抽象的成本不是「写抽象代码」的字符数，而是「未来改抽象接口」的认知负担**。延迟抽象到信息完整的时机，是策略不是拖延。

---

## Task 2 — get_product_info

**覆盖 AC**：AC5（按名搜）/ AC6（按 SKU 搜）/ AC7（无匹配）
**状态**：✅ 完成（Red → Green → 2 regression guards → 不重构）

### 测试顺序的战略选择

T2 涉及 3 条并行 AC。两种做法：

**(a) 严格 TDD 派**：写 3 个 Red 各驱动一段 Green。
- Red 1: 按名 → Green: `where(name like)`
- Red 2: 按 SKU → Green 改成 `where(or_(name like, sku like))`
- Red 3: 无匹配 → 直接绿（`[]` 是自然结果）

**(b) 实用 Detroit 派（这次选这个）**：写 1 个 Red，Green 一次性满足 spec 的并行行为，剩余 2 条作为 regression guards 直接绿。
- Red: `get_product_info("蓝牙耳机")` → 按名
- Green: `where(or_(name like, sku like))`，**预防性**覆盖 SKU 也能搜
- Regression Guard 1（直接绿）：按 SKU 搜
- Regression Guard 2（直接绿）：无匹配

**为什么选 (b)？**
- spec 已经把 3 条契约写死，**不需要再用 TDD 帮我们「发现」SKU 也要支持**
- (a) 中间会经过「按名能搜、按 SKU 不能搜」的中间状态，留在 commit 历史里反而误导
- (b) 中 Green 用了 `or_(...)`，这点超过 Red 严格要求 —— **理论上违反「最小绿」原则**，但 spec 已锁定的并行行为是合理的预防

> **辨别什么时候 (a) 合理**：spec 没说 SKU 要支持，纯靠 TDD 倒推接口形状的项目。这次 spec 完整，不属于这种情况。

### Red 验证结果

```
ImportError: cannot import name 'get_product_info' from 'app.agent.tools'
```

行为缺失型红 ✅。

### Green 实现

`tools.py` 加了 `or_` import 和新函数：

```python
from sqlalchemy import or_, select  # ← or_ 新增

def get_product_info(query: str) -> list[dict]:
    """按商品名称或 SKU 模糊查询商品。"""
    pattern = f"%{query}%"
    with SessionLocal() as db:
        rows = db.scalars(
            select(Product).where(or_(Product.name.like(pattern), Product.sku.like(pattern)))
        ).all()
        return [
            {
                "id": p.id, "name": p.name, "sku": p.sku,
                "stock": p.stock, "price": str(p.price), "image_url": p.image_url,
            }
            for p in rows
        ]
```

### Regression Guards：直接绿也值得写

```python
def test_should_return_KB_001_when_searching_by_sku(tools_session):
    # Given (AC6: get_product_info 也支持 SKU 模糊匹配)
    seed_products(tools_session)
    result = get_product_info("KB-001")
    assert len(result) == 1
    assert result[0]["name"] == "机械键盘·87 键"


def test_should_return_empty_when_searching_unknown_product(tools_session):
    # Given (AC7: 无匹配返回空列表，不抛异常)
    seed_products(tools_session)
    result = get_product_info("不存在的商品")
    assert result == []
```

**为什么写直接绿的测试也有价值？**
- AC6 / AC7 是 spec 钉死的行为。如果未来谁把 Green 改成 `where(Product.name.like(...))`（去掉 sku 分支），AC6 测试会立刻红 —— **这就是回归护栏的意义**。
- 没有这两个 guard，spec 的「按 SKU 也能搜」「无匹配返回空」就只活在 spec.md 文字里，code 层面无人守护。
- 注释 `# Given (AC6: ...)` 让测试和 spec AC 双向追溯。

### 教学要点 6：Refactor 评估的完整推理过程

`tools.py` 现在有两段几乎一样的 dict 推导：

```python
# in list_products
return [{"id": p.id, "name": p.name, ...} for p in rows]

# in get_product_info
return [{"id": p.id, "name": p.name, ...} for p in rows]
```

是不是该抽 `_product_to_dict(p) -> dict`？

**评估清单**（每条都要回答）：

| 问题 | 答案 | 影响 |
|---|---|---|
| 当前重复几处？ | 2 | < 3，rule of three 不过 |
| 未来会到 3 处吗？ | 不会。T3/T4/T5/T6 都是 order dict，不是 product dict | 可能永远停在 2 |
| 重复的成本？ | 16 行 vs 9 行 helper，省 7 行 | modest |
| 抽出去的接口能稳定命名吗？ | 能（`_product_to_dict`） | ✅ |
| 抽出去会损失什么？ | **agno 工具契约**：函数返回 dict 的 inline 形态 = LLM 可读的 schema。helper 隐藏返回 shape。 | ❌ 大 |

**决策：不抽**。最强的反对理由是第 5 条 —— 这是 agent 工具，不是普通工具函数。**LLM 通过函数签名和返回值结构理解契约**，inline dict 是「契约即文档」。helper 抽象会让契约隐藏在私有函数里。

> **对比 parking-fee 的 Task 4 才抽常数**：那次抽 `FREE_MINUTES / HOURLY_RATE / DAILY_CAP` 是因为 3 个**业务旋钮**并存形成「家族」。我们这里是 **数据形态**，不是业务规则，没有「家族」性质。

### 教学要点 7：Refactor 决策必须是「主动拒绝」，不是「忘记考虑」

每一次绿之后，refactor 阶段都应该有这样的输出：

> 我考虑过 X 重构。它的好处是 [...]，代价是 [...]，决定不动 / 现在动。

**写在 journey 里、commit message 里、code review 评论里**。这样未来读者能看到「不是没想到，是想到了不动」。否则别人会反复试图抽出来，每次都被拒绝又不知道为什么。

---

## Task 3 — lookup_orders

**覆盖 AC**：AC1（alex 2 单）/ AC2（未知用户空列表）
**状态**：✅ 完成（Red → Green → 1 regression guard → 不重构）

### 第一次 seed 订单的连锁约束

T1/T2 只 seed `products`。T3 是第一次 seed `orders`，订单的 `product_sku` 字段有 FK 指向 `products.sku`，所以测试里**必须先 `seed_products(tools_session)` 再 `seed_orders(tools_session)`**。

```python
def test_should_return_two_orders_when_querying_alex(tools_session):
    # Given
    seed_products(tools_session)   # ← 必须在 seed_orders 之前
    seed_orders(tools_session)
    ...
```

漏掉前一行：FK 违反，`IntegrityError`。这种**测试基础设施级别的约束**很容易在写作业级别项目时忽略，但在生产场景里同样存在（任何「下单依赖商品已建」的流程都有这个顺序约束）。

### 教学要点 8：用 set 比较 ID 集合，不用 list 比较顺序

```python
assert {r["order_id"] for r in result} == {1, 2}
```

为什么不写 `assert result[0]["order_id"] == 1 and result[1]["order_id"] == 2`？

**Spec 没规定返回顺序**。`lookup_orders` 现在返回 SQLAlchemy 默认顺序（一般是插入顺序），但未来可能：
- 加 `order_by(Order.id.desc())` 让最新订单在前
- 加 `order_by(current_status)` 让运输中的优先显示
- 改成按下单时间排

**任何这些改动都不应该让 AC1 测试炸**。绑定行为「alex 有 1 号和 2 号订单」，不绑定实现「按 id 升序返回」。

> **判断方法**：测试断言失败时，问自己：「失败说明 spec 被违反了，还是说明实现细节变了？」如果是后者，断言写得太严了。

### 9 键摘要 vs 14 键详情：list/get pattern

`lookup_orders` 返回 9 键摘要，**故意不含**：
- `tracking_history`（每单 4 个事件，列表场景 token 爆炸）
- `recipient` / `address` / `phone`（列表里看不到价值）

`get_order_detail`（T4）返回 14 键详情：摘要 9 键 + 收货人 3 键 + tracking_history。

**为什么分两个 tool？** Token 经济：

| 场景 | Tool 调用 | 上下文成本 |
|---|---|---|
| 「我的订单」（列表问题）| `lookup_orders` | 9 键 × 2 单 = 中等 |
| 「订单 1 物流到哪」（具体问题）| `get_order_detail(1)` | 14 键 × 1 单 = 中等 |
| 假设合并：每次都给 LLM 完整 14 键 × N 单 | — | 列表场景爆炸 |

这是 **agent 工具设计的常见模式**（list/get pattern）—— REST API 设计里的同一原则：列表接口给摘要，详情接口给完整对象。

### Green 实现要点

```python
import json
from sqlalchemy import or_, select
from app.models import Order, Product  # ← Order 新增

def lookup_orders(username: str) -> list[dict]:
    """按用户名列出该用户的所有订单概要（不含完整物流时间线）。"""
    with SessionLocal() as db:
        rows = db.scalars(select(Order).where(Order.username == username)).all()
        result = []
        for o in rows:
            logistics = json.loads(o.logistics_info)  # ← TEXT 字段需要解析
            result.append({
                "order_id": o.id,
                "product_name": o.product_name,
                ...
                "current_status": logistics.get("current_status"),
                "tracking_no": logistics.get("tracking_no"),
                "courier": logistics.get("courier"),
            })
        return result
```

为什么不用列表推导，改用普通 for 循环？因为**每行需要先 `json.loads` 再用**。列表推导写成 `[{...} for o in rows]` 会让 `json.loads(o.logistics_info)` 在每个键的 RHS 都重复一次，3 次解析同一字符串。**性能 + 可读性双输**。

> **微教学点**：列表推导适合「每行一个变换」，不适合「每行先做几次准备再组装」。

### Refactor 决策：不抽 `_parse_logistics`

考虑过抽 `_parse_logistics(o) -> dict` helper（本质 `json.loads(o.logistics_info)`）。

**评估**：

| 问题 | 答案 | 影响 |
|---|---|---|
| helper 多大？ | 1 行 | **太薄** |
| 命名能稳定吗？ | `_parse_logistics`，但其实就是个 `json.loads` | 名字过度承诺 |
| T4 会再用吗？ | 会（拿 recipient/address/phone/tracking_history） | 第 2 处使用 |
| 即使 T4 用了，要抽吗？ | T3 要 3 键、T4 要 7 键，重叠少 | 抽出去后两边各自取 dict.get，没简化什么 |

**决策：不抽**。理由汇总：
- 1 行 helper 是**反模式**——给单行表达式起名字反而引入间接性
- 与 T2 一致：tool 函数透明性优于 DRY
- 真要重复抽象，等 T4 后看 _**实际**_ 重复形态再说

> **教学陷阱**：很多人看到 2 处一样代码就想抽。但「2 处」+「单行」+「不同上下文」往往不值得 helper。**抽象的回报来自降低未来认知负担，单行 inline 的认知负担本来就接近零**。

---

## Task 4 — get_order_detail

**覆盖 AC**：AC3（order 1 详情）/ AC4（不存在订单返 error dict）
**状态**：✅ 完成（Red → Green → 1 regression guard → 不重构）

### 教学要点 9：错误用 dict 不抛异常

`get_order_detail(999) → {"error": "order_not_found", "order_id": 999}`，**不**抛 `OrderNotFoundError`。

理由：
1. **agno tool 异常会变成 ToolCallErrorEvent**，LLM 处理麻烦——它要先识别这是 error event，再决定怎么回复。
2. **dict-as-error**：LLM 直接读出 dict，自然组织成「抱歉，未找到该订单」之类的回复，不需要任何特殊事件处理。
3. **echo `order_id`**：让 LLM 在回复里能引用用户问的那个号码（「您查询的订单 999 没有找到，请确认号码是否正确」）。

> **教学陷阱**：很多 Python 教学默认「错误用异常」。但跨进程/跨语言/跨 LLM 边界时，**异常是糟糕的接口**——结构化 dict（`{error: "code", ...}`）才是。Go 用多返回值传错误是同一思想。

---

## Task 5 — GET /api/orders

**覆盖 AC**：AC9（alex 2 单）/ AC10（未知用户空列表）/ AC11（缺参 422）
**状态**：✅ 完成（Red → Green → 2 regression guards → 不重构）

### 教学要点 10：测试 fixture 的「组合」与「层叠」

T5 引入 `api_client` fixture，**组合**了三个已有 fixture：

```python
@pytest.fixture
def api_client(client, db_session, monkeypatch):
    test_sessionmaker = sessionmaker(bind=db_session.get_bind(), ...)
    monkeypatch.setattr("app.agent.tools.SessionLocal", test_sessionmaker)
    seed_products(db_session)
    seed_orders(db_session)
    return client
```

- `client`（来自 conftest）：FastAPI TestClient + get_db 依赖覆盖
- `db_session`（来自 conftest）：内存 SQLite + 表创建
- `monkeypatch`：tools.SessionLocal 替换为测试引擎

**优点**：每层 fixture 单一职责，组合时自然层叠。新测试只 `def test(api_client)` 就拿到全套环境。

**反模式**：把所有逻辑塞进 conftest 的一个 god-fixture（`@pytest.fixture` def super_client(...) 50 行）——后续维护噩梦。

### 教学要点 11：`Query(...)` 自动 422 是契约不是实现细节

```python
def get_orders(username: str = Query(..., min_length=1)) -> list[dict]:
```

`Query(..., min_length=1)` 让 FastAPI 在 username 缺失或为空时自动返回 422。AC11 测试这个**契约**：

```python
def test_should_return_422_when_username_query_missing(api_client):
    response = api_client.get("/api/orders")  # 缺参
    assert response.status_code == 422
```

测试**直接绿**（FastAPI 行为，不是我们的代码），但仍值得写——它把「缺参就 422」这个**契约决策**钉在 code 里。如果未来某人把 `Query(...)` 改成 `Query(None)`（变可选），这个测试会立刻红。

---

## Task 6 — GET /api/orders/{order_id}

**覆盖 AC**：AC12（详情）/ AC13（不存在 404）
**状态**：✅ 完成（Red → Green → 1 regression guard → 不重构）

### 教学要点 12：HTTP 边界把「dict-as-error」翻译成 HTTPException

T4 工具返回 `{"error": "order_not_found", "order_id": 999}`。
T6 端点把它转成 HTTP 404：

```python
@router.get("/api/orders/{order_id}")
def get_order(order_id: int) -> dict:
    result = get_order_detail(order_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=f"order {order_id} not found")
    return result
```

两层接口的设计哲学不同：
- **Tool 层（agent 用）**：dict-as-error，LLM 友好
- **HTTP 层（前端用）**：HTTPException，HTTP 状态码友好

**同一份业务规则，两种边界呈现**。这是「适配器」模式的实战。

### 教学要点 13：T6 Red 出现「偶然绿」要警惕

T6 写 Red 时，AC13 测试（`/api/orders/999` → 404）**直接绿**——因为还没加 `/api/orders/{order_id}` 路由，FastAPI 默认对未定义路径返 404。

这是**伪绿**：测试通过的原因不是我们想要的（不是「我们的端点检测到不存在的订单」），而是「路由不存在」。

T6 Green 加路由后，AC13 才真的验证「我们的 404」。如果 Green 实现忘了 `if "error" in result`，AC13 会立刻红。

**判断方法**：Red 出来的瞬间问「为什么红？」如果答案是「行为缺失」，红得正当；如果答案是「测试 setup 还没让到那里」，可能是伪绿。

---

## Task 7 — POST /api/chat 协议骨架

**覆盖 AC**：AC14（content-type）/ AC15（缺字段 422）
**状态**：✅ 完成（Red → Green → 1 regression guard → 不重构）

### 教学要点 14：用 stub agent 解耦协议测试与真实 LLM

T7-T10 的核心设计决策：**Chat 端点测试不调真实 LLM**。

```python
class StubAgent:
    def __init__(self, events):
        self._events = events
    async def arun(self, *args, **kwargs):
        for ev in self._events:
            yield ev


@pytest.fixture
def chat_client(monkeypatch):
    def _build(events):
        monkeypatch.setattr("app.api.chat.get_agent", lambda: StubAgent(events))
        return TestClient(app)
    return _build
```

**为什么这是关键**：
- 真实 DeepSeek 调用：3-10s/次，烧 quota，不确定（同样输入可能输出不同）
- Stub 调用：~10ms，零成本，完全确定

**SSE 事件映射逻辑只关心「输入是什么 agno event，输出是什么 SSE 块」**。这是纯函数式映射，跟 LLM 智能无关。用 stub 喂事件、断言 SSE 输出，**完全足够覆盖映射逻辑**。

真实 LLM 的智能是 T11 + 端到端冒烟的事，跟 T7-T10 协议层解耦。

> **教学陷阱**：很多 LLM 项目第一个测试就 `assert agent.run("查订单") == "您的订单..."`。这种测试又慢又脆——LLM 的输出不可能 == 字面值。**测协议（结构）不测语义（内容）**。

### 教学要点 15：placeholder 函数 + 后期实现

T7 在 `app/agent/agent.py` 写：
```python
def get_agent():
    raise NotImplementedError("get_agent will be implemented in T11")
```

为什么不一上来就写真实 agent 工厂？
- T7-T10 的关注点是 SSE 协议，**不需要真实 agent**
- placeholder 让 chat.py 能 import + 让测试能 monkeypatch（patch 一个不存在的 attr 会失败）
- T11 才填上真实实现，符合「专注一件事一次做完」

这是 **outside-in development 的局部应用**（顶层向下），即使整体走 Detroit 派也可以局部用 London 派。

---

## Task 8 — SSE token + done 映射

**覆盖 AC**：AC16
**状态**：✅ 完成（Red → Green → 不重构，留待 T9）

### 教学要点 16：测试基础设施值得有 helper（与生产代码不同）

```python
def _parse_sse(text: str) -> list[tuple[str, dict]]:
    blocks = [b for b in text.split("\n\n") if b.strip()]
    parsed = []
    for block in blocks:
        ...
    return parsed
```

`_parse_sse` 反向解析 SSE 文本流，让断言写成：
```python
assert parsed == [("token", {"text": "hi"}), ("done", {"session_id": "s1"})]
```

而不是：
```python
assert "event: token" in body
assert '"text": "hi"' in body
...
```

**测试基础设施 helper 的标准比生产代码低**——只用 1 处也可以抽，因为它直接降低断言难度。**不要把生产代码的 rule of three 套在测试代码上**。

---

## Task 9 — SSE tool start/end 映射 + 抽 _emit helper

**覆盖 AC**：AC17
**状态**：✅ 完成（Red → Green → **Refactor: 抽 _emit**）

### 教学要点 17：终于到了「抽抽象」的时刻

T9 Green 加完 `tool/start` + `tool/end` 两个 isinstance 分支后，chat.py 里有 4 处 `f"event: X\ndata: {json.dumps(...)}\n\n"`：
- token
- tool/start
- tool/end
- done

**Rule of three 跨越**。抽：

```python
def _emit(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
```

if/elif 链变成清晰的「event class → SSE type + payload mapping」：
```python
if isinstance(ev, RunContentEvent): yield _emit("token", {"text": ev.content})
elif isinstance(ev, ToolCallStartedEvent): yield _emit("tool", {"name": ev.tool.tool_name, "phase": "start"})
...
```

**关键**：T2-T8 拒绝抽 `_product_to_dict` / `_parse_logistics`，T9 主动抽 `_emit`。差别是什么？

| | `_product_to_dict` | `_emit` |
|---|---|---|
| 重复几处？ | 2 处（T1+T2） | 4 处 |
| 模板复杂度 | 8 行 dict 推导 | 1 行 f-string + json.dumps |
| 抽出去隐藏什么？ | dict shape 是 LLM 契约，不能藏 | SSE 格式是技术细节，能藏 |
| 改抽象的成本 | 高（多个 caller 期待 shape 变化） | 低（一个内部 helper） |

**rule of three 不是教条**，配合「抽出去会损失什么」一起评估。`_emit` 抽出去**反而提升可读性**——不是 DRY，是降噪。

---

## Task 10 — SSE error 映射 + endpoint 兜底

**覆盖 AC**：AC18
**状态**：✅ 完成（Red → Green → 不重构）

### 教学要点 18：超过 Red 要求加防御代码的取舍

T10 Green 不只加 `RunErrorEvent` 的 isinstance 分支（Red 要求），还把整个 `async for` 包了 `try/except`：

```python
async def sse():
    try:
        async for ev in agent.arun(...):
            ...
            elif isinstance(ev, RunErrorEvent):
                yield _emit("error", {"message": ev.content})
                return
    except Exception as e:  # noqa: BLE001 — endpoint-level fallback for Q4-A UX
        yield _emit("error", {"message": str(e)})
```

`try/except` 没有具体测试驱动。严格 TDD 派会拒绝这种「测试外」代码。

**这次接受的理由**：
- Q4-A 把「error UX」钉死了 spec 决策——「用户永远看到 error event，不看到 500」
- agno 的 `arun` 在某些极端情况（API key 错误、网络故障）会**抛异常而非 yield error event**
- 这是同一个责任的两面，分开两个任务反而割裂

**注释 `# noqa: BLE001` 是关键**：明确说「我知道 bare except 是 lint 警告，但这是有意的兜底」。**用 lint disable 当做留言条**，让 reviewer 知道这不是疏忽。

---

## Task 11 — 真实 agent factory

**覆盖 AC**：无具体 AC（构造性测试）
**状态**：✅ 完成（Red → Green → 不重构）

### 教学要点 19：构造性测试与行为测试的区别

T11 测试不调 LLM、不发请求，只验证「构造出的 Agent 实例是否符合 spec」：

```python
agent = get_agent()
assert isinstance(agent, Agent)
tool_names = {t.__name__ for t in agent.tools}
assert tool_names == {"list_products", "get_product_info", "lookup_orders", "get_order_detail"}
assert "<faq>" in agent.instructions
assert agent.add_history_to_context is True
assert agent.num_history_runs == 10
```

这是**构造性测试（构造对象后验证内部状态）**，不是**行为测试（调用方法后验证返回）**。

构造性测试的价值：
- 配置错误立刻发现（少注册 1 个工具会立刻红）
- 不依赖外部服务（可以在 CI 里跑）
- 速度快（~10ms）

**何时用构造性测试**：当对象构造本身就是关键决策时（如 dependency wiring、配置加载）。这时「构造对了」就是「行为对了」的前置条件。

### 教学要点 20：fresh_agent_module fixture 重置单例

```python
@pytest.fixture
def fresh_agent_module(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from app.agent import agent as agent_mod
    monkeypatch.setattr(agent_mod, "_agent", None, raising=False)
    return agent_mod
```

`get_agent()` 是单例（global `_agent`）。多个测试如果不重置，后续测试拿到的是首次构造的实例——破坏隔离性。

`monkeypatch.setattr(..., None)` 在每个测试前把 `_agent` 重置为 None，强制下次 `get_agent()` 重新构造。pytest 拆 fixture 时自动 unpatch。

**单例 + 测试隔离的标准模式**。Java 里的 @Before/@After 同思想。

---

## Task 12 — main.py 接线

**覆盖 AC**：无具体 AC（接线任务）
**状态**：✅ 完成

### 任务内容

- `pyproject.toml`：加 `agno>=2.6` / `openai>=1.0` / `python-dotenv>=1.0`
- `main.py`：`from dotenv import load_dotenv` + `load_dotenv()`
- `main.py`：`app.include_router(chat_api.router)`
- `.env`：写入 `DEEPSEEK_API_KEY`（gitignored）
- `.env.example`：模板（入库）

### 教学要点 21：接线任务也算一个 task

T12 没有新 Red 测试驱动，只是「把零件装起来」。但仍单独成一个 task：

- **commit 粒度对齐功能粒度**：T11 测「agent 能构造」，T12 测「app 能起来」（隐式：所有 35 测试通过 + OpenAPI 含 4 端点）
- **风险隔离**：如果 deps 装错或 env 没加载，T12 的 commit 一目了然
- **回滚单位清晰**：未来发现 dotenv 出问题，`git revert` T12 commit 就行

**verify 检查**：
- `pytest -q` → `35 passed`
- `python -c "from app.main import app; print(app.openapi()['paths'].keys())"` → 含 `/api/chat`、`/api/orders`、`/api/orders/{order_id}`、`/api/products`

---

## F1-F3 — 前端集成

**状态**：✅ 完成（无 pytest，靠手动冒烟）

### F1 — useChat composable

`fetch + ReadableStream + TextDecoderStream` 解析 SSE。**不用 EventSource** 因为 EventSource 只支持 GET。

关键设计：**buffer 跨网络分块**。SSE 一个事件可能横跨多个 TCP 包：
```js
let buffer = ''
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  buffer += value
  const [events, remainder] = _parseSseChunk(buffer)
  buffer = remainder  // ← 残余不完整的部分留到下一轮
  for (const ev of events) { ... }
}
```

不处理 buffer 残余 = SSE 解析在网络分块边界会**丢事件**或**解析错位**。

### F2 — CsrPanel.vue

右侧 360px 滑入面板。4 类气泡（user/assistant/tool/error）。`sessionStorage` 存 session_id（Q5-A）。

**克制设计**（匹配 .impeccable.md 品牌规范）：
- 单 forest-green 强调色（发送按钮、输入聚焦边框）
- hairline 1px 边框（无圆角气泡的卡通感）
- 工具状态行用小灰字斜体（不抢注意力）
- 错误用沉稳红 + 重试按钮（不用刺眼 #ff0000）

### F3 — App.vue 集成

3 处改动：
1. `import CsrPanel`
2. `panelOpen = ref(false)` + `handleCsrClick` 改成 toggle（未登录先 toast）
3. 模板加 `<CsrPanel v-model:open=... :username=... :api-base=... />`

### 教学要点 22：前端没 TDD 也要保证质量

前端没有 pytest，但仍可控：
- `npm run build` 跑一次确认 syntax/import 干净
- 在浏览器开发者工具的 Network 看 SSE 流逐 chunk 到达
- 手动冒烟清单（plan.md F3 节）：登录、点 FAB、问订单、问 FAQ、关 tab 再开

**不能 TDD 不等于不能纪律化测试**。手动清单 + build 检查 + 心理验证（每改一处问「这会破什么」）是替代方案。

---

## Phase 6 — Verify 表

把 21 条 AC 逐条对应测试：

| # | AC | 覆盖测试 | 状态 |
|---|---|---|---|
| 1 | lookup_orders("alex") → 2 单含 9 键 | `test_should_return_two_orders_when_querying_alex` | ✅ |
| 2 | lookup_orders("nobody") → [] | `test_should_return_empty_when_user_has_no_orders` | ✅ |
| 3 | get_order_detail(1) → 14 键、已签收、4 历史 | `test_should_return_full_detail_when_order_exists` | ✅ |
| 4 | get_order_detail(999) → error dict | `test_should_return_error_dict_when_order_id_unknown` | ✅ |
| 5 | get_product_info("蓝牙耳机") → AUDIO-001 | `test_should_return_AUDIO_001_when_searching_by_chinese_name` | ✅ |
| 6 | get_product_info("KB-001") → 机械键盘 | `test_should_return_KB_001_when_searching_by_sku` | ✅ |
| 7 | get_product_info("不存在") → [] | `test_should_return_empty_when_searching_unknown_product` | ✅ |
| 8 | list_products() → 8 件 | `test_should_return_8_products_when_listing_all` | ✅ |
| 9 | GET /api/orders?username=alex → 200 + 2 单 | `test_should_return_alex_orders_when_get_orders_by_username` | ✅ |
| 10 | GET /api/orders?username=nobody → 200 + [] | `test_should_return_empty_list_when_username_has_no_orders` | ✅ |
| 11 | GET /api/orders 缺参 → 422 | `test_should_return_422_when_username_query_missing` | ✅ |
| 12 | GET /api/orders/1 → 200 + 14 键 + 4 历史 + 已签收 | `test_should_return_order_detail_when_get_by_id` | ✅ |
| 13 | GET /api/orders/999 → 404 + detail | `test_should_return_404_when_order_id_unknown` | ✅ |
| 14 | POST /api/chat 合法 → 200 + text/event-stream | `test_should_return_event_stream_content_type_when_post_chat` | ✅ |
| 15 | POST /api/chat 缺字段 → 422 | `test_should_return_422_when_chat_field_missing` | ✅ |
| 16 | SSE token + done 映射 | `test_should_emit_token_and_done_when_agent_yields_content_then_completed` | ✅ |
| 17 | SSE tool start/end 映射 | `test_should_emit_tool_start_and_end_when_agent_calls_tool` | ✅ |
| 18 | SSE error 映射 + HTTP 不报 500 | `test_should_emit_error_when_agent_yields_run_error` | ✅ |
| 19 | 点 FAB 开右侧面板 | F3 手动冒烟 | ⏳ 待用户烟测 |
| 20 | 流式渲染 + 工具状态行 | F3 手动冒烟 | ⏳ 待用户烟测 |
| 21 | Session 隔离（多 tab 多用户） | F3 手动冒烟 | ⏳ 待用户烟测 |

**自动化覆盖**：18/21 条 AC（85%）。剩 3 条是 UI 级行为，spec 规定走手动冒烟（plan.md F3 节列了清单）。

**额外覆盖**：1 条「构造性测试」（T11 agent factory，无对应 AC，但保证零件装得对）。

### Verify 副产品：spec 漏洞清单

跑完发现 spec 没明确定义的灰色地带（不是 bug，是 spec 不完整）：

1. **多 token 拼接**：spec AC16 只测了「单个 RunContentEvent」。真实 LLM 会 yield 几十个 RunContentEvent，每次 1-3 字符。当前实现按顺序 append 在 chat.py 里，但 useChat 在前端做拼接时没测。手动冒烟会发现。
2. **工具调用错误（ToolCallErrorEvent）**：spec 没定义。当前 chat.py 没分支，会被忽略。如果 tool 抛了异常，agent 看不到，可能继续幻觉。**spec 漏洞**。
3. **多个并发用户**：agno SqliteDb 的 SQLite 在并发写场景下可能锁。生产场景需 PostgreSQL。spec Non-goals 没明确说。
4. **空响应**：如果 LLM 一句话都不说就 done，前端 assistant 气泡会是空字符串。spec 没规定 UX。
5. **重试按钮的 session 行为**：错误后点重试，是用同一 session_id 还是新建？当前实现用同一 session_id，但 spec 没钉。

这些放进 backlog，不影响本次「全绿验收」。

---

## 总结：实施过程中浮现的纪律

1. **Spec 的 Q&A 比 AC 数字还重要**。Q1 一开始锁 A，中途 pivot 到「数据用中文」（Phase 1 amendment）让所有翻译复杂度消失。**写 spec 不是把已知决策抄一遍，是逼出隐性决策**。
2. **测试断言绑行为，不绑实现**。Phase 1 测试用 `{s.value for s in TrackingStatus}` 让 enum 中文化重构零成本；T3 用 `set` 比较 order_id 让排序变更不会炸测试。
3. **Detroit vs London 派系是工具不是教条**。spec 完整、依赖成熟时走 Detroit（底层向上）；spec 模糊、接口未知时走 London。我们这次走 Detroit，理由全部写在 journey「为什么底层向上」节。
4. **TDD 真正的纪律是 Refactor 阶段的「不动」**。T1-T8 共 8 次 refactor 评估，7 次决定不动。每次都明确写出「考虑了 X，不抽因为 Y」——**主动拒绝**，不是「忘了考虑」。
5. **Rule of three 不是教条，配合「抽出去隐藏什么」一起评估**。T9 抽 `_emit`（4 处使用 + 抽出去提升可读性），T2 不抽 `_product_to_dict`（2 处使用 + 抽出去隐藏 LLM 契约）。
6. **测试基础设施 helper 的标准比生产代码低**。`_parse_sse` 只用一处也抽，因为它直接降低断言难度——不能用「rule of three」反对它。
7. **「不调真实 LLM」是 LLM 项目 TDD 的核心**。stub agent + 注入事件让 SSE 协议测试快、稳、确定。真实 LLM 的智能留给 T11 + 端到端冒烟。
8. **错误用 dict 不抛异常（跨进程边界）**。tool 返回 `{error: ...}` 让 LLM 自然处理；HTTP 边界再翻成 HTTPException。**同一规则在不同边界呈现不同**。
9. **「placeholder + 后期实现」是 outside-in 的局部应用**。T7-T10 用 placeholder `get_agent` 不实现，T11 才填上。Detroit 整体 + London 局部可以共存。
10. **构造性测试在 wiring 任务里至关重要**。T11 没有「行为测试」，只验证「构造对了」——这就足以保证生产能起来。
11. **接线 task 也值得独立 commit**。T12 只做 `load_dotenv` + `include_router`，但 commit 粒度对齐功能粒度，未来 revert 一目了然。
12. **手动冒烟清单是前端 TDD 的替代方案**。前端不能 TDD（UI 是视觉），但可以：build 检查 + 浏览器 devtools + 清晰的手动清单。

---

## 最终产出

```
customer-service/
├── backend/
│   ├── .env                              # gitignored，含 DEEPSEEK_API_KEY
│   ├── .env.example                      # 模板入库
│   ├── pyproject.toml                    # 加 agno + openai + python-dotenv
│   ├── app/
│   │   ├── main.py                       # 加 load_dotenv + 2 个 include_router
│   │   ├── schemas.py                    # Phase 1 amendment：TrackingStatus 中文化
│   │   ├── seed.py                       # Phase 1 amendment：所有 status 中文
│   │   ├── agent/                        # 新增
│   │   │   ├── agent.py                  # T11 真实 factory
│   │   │   ├── faq.md                    # ~80 行 FAQ markdown
│   │   │   ├── knowledge.py              # 加载 faq.md
│   │   │   └── tools.py                  # T1-T4 4 个工具
│   │   └── api/                          # 新增
│   │       ├── chat.py                   # T7-T10 SSE 端点
│   │       └── orders.py                 # T5-T6 REST 端点
│   └── tests/                            # 9 个测试文件，35 个测试，全绿
│       ├── test_agent_factory.py         # T11
│       ├── test_agent_tools.py           # T1-T4（6 测试）
│       ├── test_chat_api.py              # T7-T10（5 测试）
│       ├── test_orders_api.py            # T5-T6（5 测试）
│       └── (Phase 1 原有 5 文件 16 测试)
├── frontend/src/
│   ├── App.vue                           # F3 改 3 处
│   ├── composables/useChat.js            # F1 SSE 解析
│   └── components/CsrPanel.vue           # F2 右侧面板
└── specs/csr-agent/
    ├── spec.md                           # 21 AC，5 个 Q 全 A
    ├── plan.md                           # 12 后端 + 3 前端
    └── journey.md                        # 本文件
```

**测试套件**：`cd backend && pytest -q` → `35 passed in ~0.1s`
**OpenAPI**：`/api/products` `/api/orders` `/api/orders/{order_id}` `/api/chat`
**前端构建**：`cd frontend && npm run build` → `built in ~300ms, ~32 KB gzip JS`

剩余 = 用户启 `uvicorn` + `npm run dev` 端到端冒烟（验证 AC19-21 + Q4 重试按钮 + Q5 sessionStorage）。
