from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Callable

from models import OrderCancellationResult
from base import OrderAPIBase

UTC = timezone.utc


class OrderAPILocalClient(OrderAPIBase):
    """A local mock."""
    def __init__(self):
        # seed some orders
        now = datetime.now(UTC)
        self._orders: Dict[str, Dict[str, Any]] = {
            "ORD-4567": {
                "orderId": "ORD-4567",
                "placed_at": (now - timedelta(hours=5)).isoformat(),
                "status": "processing",
                "eta": (now + timedelta(days=2)).date().isoformat(),
            },
            "ORD-1234": {
                "orderId": "ORD-1234",
                "placed_at": (now - timedelta(days=2)).isoformat(),
                "status": "shipped",
                "eta": (now + timedelta(days=1)).date().isoformat(),
            },
        }

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self._orders.get(order_id)

    def cancel_order(self, order_id: str) -> OrderCancellationResult:
        order = self._orders.get(order_id)
        if not order:
            return OrderCancellationResult.failure(status="not_found", reason="order not found")
        placed_at = datetime.fromisoformat(order["placed_at"]).replace(tzinfo=timezone.utc)
        if datetime.now(UTC) - placed_at > timedelta(hours=24):
            return OrderCancellationResult.failure(status="ineligible", reason=">24h window")
        return OrderCancellationResult.success(status="cancelled", refunded=True)

    def track_order(self, order_id: str) -> Dict[str, Any]:
        order = self._orders.get(order_id)
        if not order:
            return {"status": "not_found"}
        return {"status": order["status"], "eta": order["eta"]}