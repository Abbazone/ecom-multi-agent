from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Callable


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
