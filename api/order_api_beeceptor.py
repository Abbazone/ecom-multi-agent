import os
import httpx
import logging
import time
from typing import (
    Any,
    Dict,
    Optional,
)

from base import OrderAPIBase
from models import OrderCancellationResult

BEECEPTOR_BASE = os.getenv("BEECEPTOR_BASE_URL", "https://ecom-mock.free.beeceptor.com").rstrip("/")
HTTPX_TIMEOUT = float(os.getenv("HTTPX_TIMEOUT", "5.0"))
HTTPX_MAX_RETRIES = int(os.getenv("HTTPX_MAX_RETRIES", "3"))
HTTPX_BACKOFF_FACTOR = float(os.getenv("HTTPX_BACKOFF_FACTOR", "0.5"))


class OrderAPIBeeceptorClient(OrderAPIBase):
    def __init__(self):
        self.base = BEECEPTOR_BASE
        self.client = httpx.Client(timeout=HTTPX_TIMEOUT)
        self.logger = logging.getLogger("app")

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def _retry_request(self, method: str, path: str) -> Optional[httpx.Response]:
        delay = HTTPX_BACKOFF_FACTOR
        last_exc = None
        for attempt in range(1, HTTPX_MAX_RETRIES + 1):
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
        self.logger.error(f"All {HTTPX_MAX_RETRIES} attempts failed for {path}: {last_exc}")
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
        if resp.status_code == 404:
            return OrderCancellationResult.failure(status=result['status'], reason=result['reason'])
        return OrderCancellationResult.success(status=result['status'], refunded=result['refunded'])

    def track_order(self, order_id: str) -> Dict[str, Any]:
        resp = self._retry_request('GET', f"/orders/{order_id}/track")
        if not resp:
            return {"status": "error"}
        if resp.status_code == 404:
            return {"status": "not_found"}
        return resp.json()
