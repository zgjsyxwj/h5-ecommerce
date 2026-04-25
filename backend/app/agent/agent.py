from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.deepseek import DeepSeek

from app.agent.knowledge import FAQ_MARKDOWN
from app.agent.tools import (
    get_order_detail,
    get_product_info,
    list_products,
    lookup_orders,
)

_INSTRUCTIONS = (
    "你是 H5 商城的中文智能客服。回复简洁克制，避免堆表情和感叹号。\n"
    "查订单/物流必须调用 lookup_orders 或 get_order_detail，严禁编造订单号、运单号、时间。\n"
    "查商品必须调用 get_product_info 或 list_products。\n"
    "政策性问题必须引用下方 <faq> 内容；找不到就坦诚说「该问题暂无明确说明，建议联系人工客服」。\n"
    "用户身份未知（无 username）→ 答「请先登录后查询订单」。\n"
    "与商城无关的话题 → 婉拒、引导回客服话题。\n"
    f"<faq>\n{FAQ_MARKDOWN}\n</faq>"
)

_db = SqliteDb(db_file="agent.db")
_agent: Agent | None = None


def get_agent() -> Agent:
    """构造并返回 agno Agent 单例。"""
    global _agent
    if _agent is None:
        _agent = Agent(
            name="智能客服",
            model=DeepSeek(id="deepseek-chat"),
            instructions=_INSTRUCTIONS,
            tools=[lookup_orders, get_order_detail, get_product_info, list_products],
            db=_db,
            add_history_to_context=True,
            num_history_runs=10,
            markdown=False,
        )
    return _agent
