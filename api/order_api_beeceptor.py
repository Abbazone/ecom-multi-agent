import os
import httpx
import logging
import time
from typing import Any, Dict, Optional

from base import OrderAPIBase
from models import OrderCancellationResult
from config.settings import settings

cfg = settings.order_api


class OrderAPIBeeceptorClient(OrderAPIBase):
    def __init__(self):
        self.base = cfg.base_url
        self.client = httpx.Client(timeout=cfg.timeout_seconds)
        self.logger = logging.getLogger("app")

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def _retry_request(self, method: str, path: str) -> Optional[httpx.Response]:
        delay = cfg.backoff_factor
        last_exc = None
        for attempt in range(1, cfg.max_retries + 1):
            try:
                if method == 'GET':
                    resp = self.client.get(self._url(path))
                else:
                    resp = self.client.post(self._url(path))
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(f"Server error {resp.status_code}", request=resp.request, response=resp)
                return resp
            except Exception as e:
                last_exc = e
                self.logger.warning(f"Attempt {attempt} failed for {path}: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2
        self.logger.error(f"All {cfg.max_retries} attempts failed for {path}: {last_exc}")
        return None

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        resp = self._retry_request('GET', f"/orders/{order_id}")
        if not resp:
            return None
        if resp.status_code == 404:
            return None
        return resp.json()

    def cancel_order(self, order_id: str) -> OrderCancellationResult:
        resp = self._retry_request('POST', f"/orders/{order_id}/cancel")
        if not resp:
            return OrderCancellationResult.failure(status="error", reason=f"empty response")
        result = resp.json()
        if resp.status_code == 404 or result['status'] != 'cancelled':
            return OrderCancellationResult.failure(status=result['status'], reason=result['reason'])
        return OrderCancellationResult.success(status=result['status'], refunded=result['refunded'])

    def track_order(self, order_id: str) -> Dict[str, Any]:
        resp = self._retry_request('GET', f"/orders/{order_id}/track")

        if not resp:
            return {"status": "error"}
        if resp.status_code == 404:
            return {"status": "not_found"}
        return resp.json()
