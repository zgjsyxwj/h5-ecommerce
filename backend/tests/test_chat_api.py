import json

import pytest
from agno.models.response import ToolExecution
from agno.run.agent import (
    RunCompletedEvent,
    RunContentEvent,
    RunErrorEvent,
    ToolCallCompletedEvent,
    ToolCallStartedEvent,
)
from fastapi.testclient import TestClient

from app.main import app


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """把 SSE 文本流拆成 [(event_type, data_dict), ...]。"""
    blocks = [b for b in text.split("\n\n") if b.strip()]
    parsed = []
    for block in blocks:
        lines = block.split("\n")
        event = next(line[len("event: "):] for line in lines if line.startswith("event: "))
        data = next(line[len("data: "):] for line in lines if line.startswith("data: "))
        parsed.append((event, json.loads(data)))
    return parsed


class StubAgent:
    """测试用 Agent stub。arun() 把预设事件序列 yield 出来，并记录最近一次调用。"""

    def __init__(self, events):
        self._events = events
        self.last_call = None  # (args, kwargs) tuple

    async def arun(self, *args, **kwargs):
        self.last_call = (args, kwargs)
        for ev in self._events:
            yield ev


@pytest.fixture
def chat_client(monkeypatch):
    """返回一个 (events) -> (TestClient, StubAgent) 的工厂，可拿到 stub 检查调用。"""
    def _build(events):
        stub = StubAgent(events)
        monkeypatch.setattr("app.api.chat.get_agent", lambda: stub)
        return TestClient(app), stub
    return _build


def test_should_return_event_stream_content_type_when_post_chat(chat_client):
    # Given (AC14: 合法请求 → 200 + text/event-stream content-type)
    client, _ = chat_client(events=[])

    # When
    response = client.post(
        "/api/chat",
        json={"message": "hi", "username": "alex", "session_id": "s1"},
    )

    # Then
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


def test_should_return_422_when_chat_field_missing(chat_client):
    # Given (AC15: 缺 message/username/session_id 任一 → Pydantic 422)
    client, _ = chat_client(events=[])

    # When
    response = client.post(
        "/api/chat", json={"username": "alex", "session_id": "s1"}  # 缺 message
    )

    # Then
    assert response.status_code == 422


def test_should_emit_token_and_done_when_agent_yields_content_then_completed(chat_client):
    # Given (AC16: RunContentEvent → token; RunCompletedEvent → done)
    events = [RunContentEvent(content="hi"), RunCompletedEvent(session_id="s1")]
    client, _ = chat_client(events=events)

    # When
    response = client.post(
        "/api/chat",
        json={"message": "x", "username": "alex", "session_id": "s1"},
    )

    # Then
    parsed = _parse_sse(response.text)
    assert parsed == [
        ("token", {"text": "hi"}),
        ("done", {"session_id": "s1"}),
    ]


def test_should_emit_tool_start_and_end_when_agent_calls_tool(chat_client):
    # Given (AC17: ToolCallStartedEvent → tool/start; ToolCallCompletedEvent → tool/end)
    tool = ToolExecution(tool_name="lookup_orders")
    events = [
        ToolCallStartedEvent(created_at=0, tool=tool),
        ToolCallCompletedEvent(created_at=0, tool=tool),
        RunCompletedEvent(session_id="s1"),
    ]
    client, _ = chat_client(events=events)

    # When
    response = client.post(
        "/api/chat",
        json={"message": "x", "username": "alex", "session_id": "s1"},
    )

    # Then
    parsed = _parse_sse(response.text)
    assert parsed == [
        ("tool", {"name": "lookup_orders", "phase": "start"}),
        ("tool", {"name": "lookup_orders", "phase": "end"}),
        ("done", {"session_id": "s1"}),
    ]


def test_should_emit_error_when_agent_yields_run_error(chat_client):
    # Given (AC18: RunErrorEvent → error event；HTTP 仍 200，不报 500)
    events = [RunErrorEvent(content="api timeout")]
    client, _ = chat_client(events=events)

    # When
    response = client.post(
        "/api/chat",
        json={"message": "x", "username": "alex", "session_id": "s1"},
    )

    # Then
    assert response.status_code == 200
    parsed = _parse_sse(response.text)
    assert parsed == [("error", {"message": "api timeout"})]


def test_should_inject_username_into_agent_prompt(chat_client):
    # Given (regression guard: spec gap from Phase 6 verify —
    # username 必须注入 LLM 可见的 prompt 上下文，否则 agent 不知道
    # 该传给 lookup_orders 的是哪个用户)
    events = [RunCompletedEvent(session_id="s1")]
    client, stub = chat_client(events=events)

    # When
    client.post(
        "/api/chat",
        json={"message": "我的订单到哪了", "username": "alex", "session_id": "s1"},
    )

    # Then
    assert stub.last_call is not None
    args, kwargs = stub.last_call
    prompt = args[0]
    assert "alex" in prompt          # username 在 prompt 里
    assert "我的订单到哪了" in prompt  # 用户原始 message 也在
    assert kwargs["user_id"] == "alex"   # agno 用这个分隔 session
    assert kwargs["session_id"] == "s1"
    assert kwargs["stream"] is True
    assert kwargs["stream_events"] is True
