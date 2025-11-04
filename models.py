from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


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


@dataclass(frozen=True)
class OrderCancellationResult:
    status: str
    refunded: Optional[str] = None
    reason: Optional[str] = None

    @staticmethod
    def success(status: str, refunded: str) -> "OrderCancellationResult":
        return OrderCancellationResult(status=status, refunded=refunded, reason=None)

    @staticmethod
    def failure(status: str, reason: str) -> "OrderCancellationResult":
        return OrderCancellationResult(status=status, refunded=None, reason=reason)
