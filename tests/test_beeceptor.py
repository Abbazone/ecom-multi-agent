import json
import httpx
import pytest
from api.order_api_beeceptor import OrderAPIBeeceptorClient


BEECEPTOR_BASE = "https://ecom-mock.free.beeceptor.com"


@pytest.fixture
def client():
    return OrderAPIBeeceptorClient(BEECEPTOR_BASE)


def test_get_order_exists_4567(httpx_mock, client):
    url = f"{BEECEPTOR_BASE}/orders/ORD-4567"
    payload = {
        "orderId": "ORD-4567",
        "placed_at": "2025-10-25T06:00:00",
        "status": "processing",
        "eta": "2025-10-27T08:00:00"
    }
    httpx_mock.add_response(method="GET", url=url, status_code=200, json=payload)
    result = client.get_order("ORD-4567")
    # expected = {"orderId": "ORD-4567", "status": "shipped"}
    # assert result["status"] == "shipped", f"got result={result}, expected{expected}"
    assert result == payload, f"got result={result}, expected{payload}"


def test_get_order_exists_1234(httpx_mock, client):
    url = f"{BEECEPTOR_BASE}/orders/ORD-1234"
    payload = {
      "orderId": "ORD-1234",
      "placed_at": "2025-10-23T06:00:00",
      "status": "shipped",
      "eta": "2025-10-26T08:00:00"
    }
    httpx_mock.add_response(method="GET", url=url, status_code=200, json=payload)

    result = client.get_order("ORD-1234")
    assert result == payload


def test_get_order_not_found_returns_none(httpx_mock, client):
    url = f"{BEECEPTOR_BASE}/orders/ORD-9999"
    httpx_mock.add_response(method="GET", url=url, status_code=404)

    result = client.get_order("ORD-9999")
    assert result is None


def test_cancel_order_recent_allowed(httpx_mock, client):
    url = f"{BEECEPTOR_BASE}/orders/ORD-4567/cancel"
    httpx_mock.add_response(method="POST", url=url, status_code=200, json={"status": "cancelled"})

    result = client.cancel_order("ORD-4567")
    assert result == {"status": "cancelled"}


def test_cancel_order_old_too_late(httpx_mock, client):
    url = f"{BEECEPTOR_BASE}/orders/ORD-1234/cancel"
    httpx_mock.add_response(method="POST", url=url, status_code=200, json={"status": "too_late"})

    result = client.cancel_order("ORD-1234")
    assert result == {"status": "too_late"}


def test_cancel_order_not_found_maps_to_not_found(httpx_mock, client):
    url = f"{BEECEPTOR_BASE}/orders/ORD-9999/cancel"
    httpx_mock.add_response(method="POST", url=url, status_code=404)

    result = client.cancel_order("ORD-9999")
    assert result == {"status": "not_found"}


# def test_track_order_existing(httpx_mock, client):
#     url = f"{BEECEPTOR_BASE}/orders/ORD-1234/track"
#     payload = {
#         "orderId": "ORD-1234",
#         "status": "shipped",
#         "history": [
#             {"ts": "2025-10-23T08:00:00Z", "event": "Order received"},
#             {"ts": "2025-10-24T09:15:00Z", "event": "Dispatched from warehouse"},
#         ],
#     }
#     httpx_mock.add_response(method="GET", url=url, status_code=200, json=payload)
#
#     result = client.track_order("ORD-1234")
#     assert result == payload
#
#
# def test_track_order_not_found_maps_to_not_found(httpx_mock, client):
#     url = f"{BEECEPTOR_BASE}/orders/ORD-0001/track"
#     httpx_mock.add_response(method="GET", url=url, status_code=404)
#
#     result = client.track_order("ORD-0001")
#     assert result == {"status": "not_found"}
#
#
# def test_get_order_network_error_returns_none(httpx_mock, client):
#     url = f"{BEECEPTOR_BASE}/orders/ORD-4567"
#     httpx_mock.add_exception(method="GET", url=url, exception=httpx.ConnectError("boom"))
#
#     result = client.get_order("ORD-4567")
#     assert result is None
#
#
# def test_cancel_order_network_error_returns_error(httpx_mock, client):
#     url = f"{BEECEPTOR_BASE}/orders/ORD-4567/cancel"
#     httpx_mock.add_exception(method="POST", url=url, exception=httpx.ReadTimeout("slow"))
#
#     result = client.cancel_order("ORD-4567")
#     assert result == {"status": "error"}
#
#
# def test_track_order_network_error_returns_error(httpx_mock, client):
#     url = f"{BEECEPTOR_BASE}/orders/ORD-4567/track"
#     httpx_mock.add_exception(method="GET", url=url, exception=httpx.TransportError("nope"))
#
#     result = client.track_order("ORD-4567")
#     assert result == {"status": "error"}
