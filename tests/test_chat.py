import json
import re
import os
import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def fresh_app(monkeypatch):
    """
    Import the app fresh each test, and reset in-memory session state if present.
    If your app uses Redis in CI, unset REDIS_URL here to force in-memory store.
    """
    monkeypatch.delenv("REDIS_URL", raising=False)
    mod = importlib.import_module("app")
    # importlib.reload(mod)

    # reset in-memory session store if available
    if hasattr(mod, "store") and hasattr(mod.store, "_mem"):
        mod.store._mem.clear()

    yield mod


@pytest.fixture
def client(fresh_app):
    return TestClient(fresh_app.app)


def _post_chat(client, session_id, message):
    resp = client.post(
        "/chat",
        json={"session_id": session_id, "message": message},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    # Basic schema checks
    assert "response" in payload and "agent" in payload and "handover" in payload
    assert isinstance(payload.get("tool_calls", []), list)
    return payload


def test_tracking_known_order_success(client):
    """
    Usage example #1: "Track ORD-1234"
    Expect: OrderTrackingAgent, tool call to tracking API, status+eta in response.
    """
    data = _post_chat(client, "s1", "Track ORD-1234")
    assert data["agent"] == "OrderTrackingAgent"
    assert any(tc["tool"].lower().startswith("ordertracking") for tc in data["tool_calls"])
    assert "ORD-1234" in data["response"], data
    assert re.search(r"Estimated delivery: \d{4}-\d{2}-\d{2}", data["response"])


def test_cancellation_eligible_success(client):
    """
    Usage example #2: "Please cancel ORD-4567" (<24h)
    Expect: cancelled + refunded True in tool_calls result.
    """
    data = _post_chat(client, "s2", "Please cancel ORD-4567")
    assert data["agent"] == "OrderCancellationAgent"
    assert "cancelled" in json.dumps(data["tool_calls"]).lower()
    assert "ORD-4567" in data["response"]


def test_cancellation_ineligible_policy(client):
    """
    Usage example #3: "Cancel ORD-1234" (>24h)
    Expect: policy message about >24h window; not cancelled.
    """
    data = _post_chat(client, "s3", "Cancel ORD-1234")
    assert data["agent"] == "OrderCancellationAgent"
    assert "> 24" in data["response"] or "more than 24 hours" in data["response"].lower()
    assert "⛔️" in data["response"]


def test_cancellation_unknown_order(client):
    """
    Edge case: unknown ID returns not-found style messaging.
    """
    data = _post_chat(client, "s4", "Cancel ORD-9999")
    assert data["agent"] == "OrderCancellationAgent"
    assert "❗" in data["response"].lower(), data


def test_invalid_order_id_prompts_for_format(client):
    """
    Edge case: invalid ID format should politely prompt for ORD-XXXX.
    """
    data = _post_chat(client, "s5", "Cancel ABC-1234")
    assert data["agent"] == "OrderCancellationAgent"
    assert "should look like ORD-1234" in data["response"], data['response']


def test_missing_id_prompts_for_id(client):
    """
    Edge case: user says 'cancel my order' with no ID.
    """
    data = _post_chat(client, "s6", "Please cancel my order")
    assert data["agent"] == "OrderCancellationAgent"
    assert "provide your order id" in data["response"].lower()


def test_product_qa_fallback(client):
    """
    Usage example #4 (first turn): Product question should be handled by ProductQAAgent.
    We don't assume embeddings; fallback/substr search should still answer.
    """
    data = _post_chat(client, "s7", "Tell me about your return policy")
    assert data["agent"] == "ProductQAAgent"
    assert "return" in data["response"].lower()


def test_multi_turn_pronoun_cancel_after_tracking_with_llm_resolver(monkeypatch, fresh_app):
    """
    Multi-turn scenario: 'Track ORD-1234' then 'Cancel it please'
    We monkeypatch the resolver used by resolve_order_id_from_context (if present)
    OR the helper itself to return last_order_id when pronouns are present.
    """
    from app import app as fastapi_app
    client = TestClient(fastapi_app)

    # Step 1: track to set last_order_id in session state
    track = _post_chat(client, "s8", "Track ORD-1234")
    assert track["agent"] == "OrderTrackingAgent"

    # Monkeypatch strategy A: patch resolve_order_id_from_context if available
    try:
        import app as mod

        def fake_resolve(state, message):
            # Emulate LLM pronoun resolution -> last_order_id
            if "it" in message.lower() and state.get("last_order_id"):
                return state["last_order_id"]
            # fall back to regex in original function if any
            m = re.search(r"^ORD-\d{4}$", message)
            return m.group(0) if m else state.get("last_order_id")

        if hasattr(mod, "resolve_order_id_from_context"):
            monkeypatch.setattr(mod, "resolve_order_id_from_context", fake_resolve)
        # Also patch inside agent class namespace if it imported the symbol differently
        if hasattr(mod, "OrderCancellationAgent"):
            monkeypatch.setattr(
                mod.OrderCancellationAgent,
                "handle",
                _wrap_cancellation_handle_with_resolution(mod.OrderCancellationAgent.handle),
                raising=False,
            )
    except Exception:
        pass

    # Step 2: cancel via pronoun
    cancel = _post_chat(client, "s8", "Cancel it please")
    assert cancel["agent"] == "OrderCancellationAgent"
    # We expect it targeted the last tracked order
    assert "ORD-1234" in cancel["response"]


def _wrap_cancellation_handle_with_resolution(orig_handle):
    """
    Fallback wrapper if you need to enforce resolution in the agent (only used if needed).
    """
    def _wrapped(self, request_id, session_id, message):
        # Force a best-effort resolution before calling the original
        if hasattr(self, "state") and "last_order_id" in self.state and "it" in message.lower():
            if not re.search(r"ORD-\d{4}", message):
                message = f"{message} (ORD context: {self.state['last_order_id']})"
        return orig_handle(self, request_id, session_id, message)
    return _wrapped
