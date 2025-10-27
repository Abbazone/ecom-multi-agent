from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    Optional
)

from models import OrderCancellationResult

class BaseKVStorage(ABC):

    @abstractmethod
    def search(self, query: str) -> Dict[str, Any]:
        """Search storage"""


class OrderAPIBase(ABC):

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order"""

    @abstractmethod
    def cancel_order(self, order_id: str) -> OrderCancellationResult:
        """Cancel order"""

    @abstractmethod
    def track_order(self, order_id: str) -> Dict[str, Any]:
        """Track order"""


# class RouterBase(ABC):
#
#     @abstractmethod
#     def route(self,  text: str) -> Tuple[Intent, float, Dict[str, Any]]
#         """Intent router"""
