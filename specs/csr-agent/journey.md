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

## 后续待补充

> 本文档将随 Phase 3-6 推进持续追加。当前进度：
> - ✅ Phase 1 — Specify（含 Q1 中途 pivot）
> - ✅ Phase 1 Amendment（中文枚举）
> - ✅ Phase 2 — Plan（含 Detroit vs London 派系讨论）
> - ✅ Task 1 — list_products
> - ✅ Task 2 — get_product_info（含 regression guards）
> - ✅ Task 3 — lookup_orders（含 AC2 guard、list/get pattern 讨论）
> - ⏸️ Task 4-12 / F1-F3
> - ⏸️ Phase 6 — Verify 表
> - ⏸️ 最终回顾纪律
