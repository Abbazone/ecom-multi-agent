import json, re, importlib, pytest
from fastapi.testclient import TestClient

SCENARIOS = [
    {
        "name": "track_known_order",
        "turns": [
            {"in": "Track ORD-1234",
             "expect": {"agent": "OrderTrackingAgent",
                        "tool": "OrderTrackingAPI",
                        "contains": ["ORD-1234", "Estimated"]}},
        ],
    },
    {
        "name": "cancel_eligible",
        "turns": [
            {"in": "Please cancel ORD-4567",
             "expect": {"agent": "OrderCancellationAgent",
                        "tool": "OrderCancellationAPI",
                        "contains": ["✅", "ORD-4567"]}},
        ],
    },
    {
        "name": "cancel_ineligible_policy",
        "turns": [
            {"in": "Cancel ORD-1234",
             "expect": {"agent": "OrderCancellationAgent",
                        "tool": "OrderCancellationAPI",
                        "contains": ["⛔️", "ineligible"]}},
        ],
    },
    # TODO fix logic of these evals
    # {
    #     "name": "multi_turn_pronoun_cancel_after_track",
    #     "turns": [
    #         {"in": "Track ORD-1234", "expect": {"tool": "OrderTrackingAPI"}},
    #         {"in": "Cancel it please",
    #          "expect": {"tool": "OrderCancellationAPI", "contains": ["ORD-1234"]}},
    #     ],
    #     "mock_llm": {"resolved_order_id": "ORD-1234", "confidence": 0.9, "reasoning": "pronoun → last_order_id"},
    # },
    # {
    #     "name": "kb_answer_with_citations",
    #     "turns": [
    #         {"in": "how long do I have to send items back?",
    #          "expect": {"tool": "KBSearch", "contains": ["return", "30"]}},
    #     ],
    # },
]

@pytest.fixture(autouse=True)
def fresh_app(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    mod = importlib.import_module("app")
    importlib.reload(mod)
    if hasattr(mod, "store") and hasattr(mod.store, "_mem"):
        mod.store._mem.clear()

    # Deterministic intent
    if hasattr(mod, "LLMRouter"):
        class _FakeIntent(mod.LLMIntentDecider):
            def decide(self, message, state):
                m = message.lower()
                mm = re.search(r"ORD-\d{4}", message)
                if "cancel" in m:
                    return {"intent":"cancel","order_id": mm.group(0) if mm else None, "query": None, "confidence": 0.9, "reason":"rule"}
                if "track" in m or "status" in m or "where is" in m:
                    return {"intent":"track","order_id": mm.group(0) if mm else None, "query": None, "confidence": 0.9, "reason":"rule"}
                return {"intent":"kb","order_id": None, "query": message, "confidence": 0.9, "reason":"rule"}
        monkeypatch.setattr(mod, "LLMRouter", _FakeIntent)

    yield mod

@pytest.fixture
def client(fresh_app):
    return TestClient(fresh_app.app)

def post_chat(client, sid, msg):
    r = client.post("/chat", json={"session_id": sid, "message": msg})
    assert r.status_code == 200, r.text
    return r.json()

@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["name"] for s in SCENARIOS])
def test_scenarios(client, fresh_app, scenario, monkeypatch):
    sid = scenario["name"]
    if scenario.get("mock_llm") and hasattr(fresh_app, "LLMContextResolver"):
        class _FakeResolver(fresh_app.LLMContextResolver):
            def resolve(self, message, state):
                return scenario["mock_llm"]
        monkeypatch.setattr(fresh_app, "LLMContextResolver", _FakeResolver)

    resp = None
    for turn in scenario["turns"]:
        resp = post_chat(client, sid, turn["in"])
        assert resp["agent"] == turn['expect']['agent']
        assert len(resp.get("tool_calls", [])) >= 1
        if "tool" in turn["expect"]:
            tools = [tc["tool"] for tc in resp["tool_calls"]]
            assert any(turn["expect"]["tool"] == t for t in tools)
        for s in turn["expect"].get("contains", []):
            assert s in json.dumps(resp['response'], ensure_ascii=False)
    assert {"response", "agent", "handover", "tool_calls"} <= set(resp.keys())
