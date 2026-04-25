import pytest
from fastapi.testclient import TestClient

from app.main import app


class StubAgent:
    """测试用 Agent stub。arun() 把预设事件序列 yield 出来。"""

    def __init__(self, events):
        self._events = events

    async def arun(self, *args, **kwargs):
        for ev in self._events:
            yield ev


@pytest.fixture
def chat_client(monkeypatch):
    """返回一个 (events) -> TestClient 的工厂，每次调用换一个 stub。"""
    def _build(events):
        monkeypatch.setattr(
            "app.api.chat.get_agent",
            lambda: StubAgent(events),
        )
        return TestClient(app)
    return _build


def test_should_return_event_stream_content_type_when_post_chat(chat_client):
    # Given (AC14: 合法请求 → 200 + text/event-stream content-type)
    client = chat_client(events=[])

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
    client = chat_client(events=[])

    # When
    response = client.post(
        "/api/chat", json={"username": "alex", "session_id": "s1"}  # 缺 message
    )

    # Then
    assert response.status_code == 422
