# E‑commerce Assistant Challenge — Production‑Ready Multi‑Agent System

This repo contains a **single‑endpoint**, **multi‑agent**, **observable** customer‑service system for an e‑commerce platform. It satisfies:

* **Order Cancellation Policy** (ID format `ORD-XXXX`, < 24h, mock API call)
* **Order Tracking Policy** (ID format `ORD-XXXX`, status + ETA via mock API)
* **Product Information Policy** (FAQ/RAG from a JSON knowledge base)
* **Multi‑turn state** with `session_id` memory (in‑memory or Redis)
* **Structured outputs** with `agent`, `tool_calls`, and `handover` trail
* **Observability**: structured logging, request/agent spans, and Prometheus metrics
* **Single HTTP endpoint:** `POST /chat`

---

## Quick Start

```bash
# 1) Create a virtualenv (Python 3.10+ recommended)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) Optional: run Redis for persistent session state
# docker run -p 6379:6379 --name redis -d redis:7
# export REDIS_URL=redis://localhost:6379/0

# 3) Run the service
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 4) Try it
curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"abc123","message":"I want to cancel my order ORD-4567"}' | jq
```

* OpenAPI/Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
* Metrics: [http://localhost:8000/metrics](http://localhost:8000/metrics)
* Health: [http://localhost:8000/healthz](http://localhost:8000/healthz)

---

## Architecture (Multi‑Agent Orchestration)

```
                    ┌──────────────────────────────┐
   POST /chat  ───▶ │       OrchestratorAgent      │
                    │  (intent routing + policy)   │
                    └─────────────┬────────────────┘
                                  │handovers
          ┌───────────────────────┼──────────────────────────┐
          ▼                       ▼                          ▼
┌──────────────────┐   ┌───────────────────┐       ┌───────────────────┐
│CancellationAgent │   │ TrackingAgent     │       │ ProductQAAgent    │
│ - validate ID    │   │ - validate ID     │       │ - FAQ / RAG       │
│ - <24h window    │   │ - call tracking   │       │ - KB search       │
│ - call cancel API│   │ - format ETA      │       │ - follow-ups      │
└─────────┬────────┘   └─────────┬─────────┘       └─────────┬─────────┘
          │ tools                │ tools                      │ tools
          ▼                      ▼                            ▼
   ┌──────────────┐       ┌──────────────┐               ┌──────────────┐
   │OrderAPIClient│       │OrderAPIClient│               │ KnowledgeBase │
   │ (mock)       │       │ (mock)       │               │  (JSON/embeds)│
   └──────────────┘       └──────────────┘               └──────────────┘

                  ┌───────────────────────────────────────────────────┐
                  │ Session Store (Redis or in‑memory)                │
                  │   - state by session_id                           │
                  │   - last product context, last order ID           │
                  │   - full history for multi‑turn continuity        │
                  └───────────────────────────────────────────────────┘

      Observability: Structured logs + Prometheus metrics + handover trail
```

### Multi‑Turn State & Context

* **State schema** (per `session_id`):

  ```json
  {
    "session_id": "abc123",
    "history": [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}],
    "last_product_context": "Bluetooth headphones",
    "last_order_id": "ORD-4567",
    "created_at": "2025-10-24T17:00:00Z",
    "updated_at": "2025-10-24T17:05:00Z"
  }
  ```
* The orchestrator and agents **read/write** this dict. Example: if the user says *“Can I return my Bluetooth headphones?”* then later says *“Alright, cancel the order for that then.”*, the system uses `last_product_context` + `last_order_id` to infer intent.

### Structured Outputs

Every response returns:

```json
{
  "response": "...human‑readable reply...",
  "agent": "OrderCancellationAgent",
  "tool_calls": [
    {"tool":"OrderCancellationAPI","input":{"orderId":"ORD-4567"},"result":{"status":"cancelled","refunded":true}}
  ],
  "handover": "OrchestratorAgent → OrderCancellationAgent"
}
```

---

## Business Policies (Enforced)

**Order ID format**: `ORD-XXXX` (four digits). Regex: `^ORD-\d{4}$`

**Cancellation window**: placed **< 24 hours** ago.

**Tracking**: return discrete status + ETA date from the mock API.

**Product Info**: lookup from `kb/faq.json` (string search) or enable embeddings (RAG) via `ENABLE_EMBEDDINGS=true`.

---

## Files

* `app.py` — FastAPI app, orchestrator, agents, tools, and session store (single file for simplicity)
* `requirements.txt` — dependencies
* `kb/faq.json` — sample knowledge base
* `Dockerfile` — container image
* `docker-compose.yml` — optional Redis + app stack

---

## Tests
* ` pytest tests/test_beeceptor.py`
