from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.agent import get_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


@router.post("/api/chat")
async def chat(req: ChatRequest):
    agent = get_agent()

    async def sse():
        async for _ev in agent.arun(req.message, user_id=req.username, session_id=req.session_id):
            pass
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")
