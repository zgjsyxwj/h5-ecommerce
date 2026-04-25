import json

from agno.run.agent import (
    RunCompletedEvent,
    RunContentEvent,
    RunErrorEvent,
    ToolCallCompletedEvent,
    ToolCallStartedEvent,
)
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.agent import get_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


def _emit(event_type: str, payload: dict) -> str:
    """格式化一个 SSE 事件块。"""
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/api/chat")
async def chat(req: ChatRequest):
    agent = get_agent()

    async def sse():
        try:
            async for ev in agent.arun(
                req.message, user_id=req.username, session_id=req.session_id
            ):
                if isinstance(ev, RunContentEvent):
                    yield _emit("token", {"text": ev.content})
                elif isinstance(ev, ToolCallStartedEvent):
                    yield _emit("tool", {"name": ev.tool.tool_name, "phase": "start"})
                elif isinstance(ev, ToolCallCompletedEvent):
                    yield _emit("tool", {"name": ev.tool.tool_name, "phase": "end"})
                elif isinstance(ev, RunCompletedEvent):
                    yield _emit("done", {"session_id": ev.session_id})
                elif isinstance(ev, RunErrorEvent):
                    yield _emit("error", {"message": ev.content})
                    return
        except Exception as e:  # noqa: BLE001 — endpoint-level fallback for Q4-A UX
            yield _emit("error", {"message": str(e)})

    return StreamingResponse(sse(), media_type="text/event-stream")
