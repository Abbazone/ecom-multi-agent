from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Tuple, Callable


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Session key for multi‑turn memory")
    message: str = Field(..., description="User message")


class ToolCall(BaseModel):
    tool: str
    input: Dict[str, Any]
    result: Dict[str, Any]


class ChatResponse(BaseModel):
    response: str
    agent: str
    tool_calls: List[ToolCall] = []
    handover: str