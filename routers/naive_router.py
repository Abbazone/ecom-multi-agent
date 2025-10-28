import os
from typing import Tuple, Dict, Any
from routers import Intent


class NaiveRouter:
    @staticmethod
    def route(text: str) -> Tuple[Intent, float, Dict[str, Any]]:
        t = text.lower()
        if any(k in t for k in ["cancel", "refund this order", "call off", "undo my order"]):
            return "order_cancellation", 1.0, {"matched": "cancel-keyword"}
        if any(k in t for k in ["track", "where is", "status of", "eta"]):
            return "order_tracking", 1.0, {"matched": "track-keyword"}
        return "product_qa", 0.5, {"matched": "fallback"}
