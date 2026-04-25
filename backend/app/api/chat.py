import json

from agno.run.agent import (
    RunCompletedEvent,
    RunContentEvent,
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

    return StreamingResponse(sse(), media_type="text/event-stream")
