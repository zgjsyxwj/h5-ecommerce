import pytest
from agno.agent import Agent


@pytest.fixture(autouse=True)
def fake_api_key(monkeypatch):
    """Agent 构造不会发起 API 请求，但 DeepSeek 字段需要个非空 key。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-used")


@pytest.fixture
def fresh_agent_module(monkeypatch, tmp_path):
    """重置模块级单例 + 把 SqliteDb 引到 tmp 目录，避免测试副作用。"""
    monkeypatch.chdir(tmp_path)  # SqliteDb 默认相对路径
    from app.agent import agent as agent_mod
    monkeypatch.setattr(agent_mod, "_agent", None, raising=False)
    return agent_mod


def test_should_build_agent_with_four_tools_and_faq_in_instructions(fresh_agent_module):
    # When
    agent = fresh_agent_module.get_agent()

    # Then
    assert isinstance(agent, Agent)

    tool_names = {t.__name__ for t in agent.tools}
    assert tool_names == {"list_products", "get_product_info", "lookup_orders", "get_order_detail"}

    assert "<faq>" in agent.instructions
    assert "</faq>" in agent.instructions

    assert agent.add_history_to_context is True
    assert agent.num_history_runs == 10
