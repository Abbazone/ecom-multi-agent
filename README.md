# E‑commerce Multi‑Agent System

This repo contains a **single‑endpoint**, **multi‑agent**, **observable** customer‑service system for an e‑commerce platform. 
It satisfies:

* **Order Tracking Policy** (ID format `ORD-XXXX`, status + ETA via mock or Beeceptor API)
* **Order Cancellation Policy** (ID format `ORD-XXXX`, < 24h, mock or Beeceptor API call)
* **Product Information Policy** (FAQ/RAG from a JSON or Chroma vector knowledge bases)
* **Intent-router**(`order_cancellation`, `order_tracking` and `product_qa`, via ML, LLM or naive)
* **Multi‑turn state** with `session_id` memory (in‑memory or Redis)
* **Context-resolver** resolve `order_id` from memory with LLM.
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

Alternatively use Docker:
```bash
docker compose build
docker compose up -d
```

* OpenAPI/Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
* Metrics: [http://localhost:8000/metrics](http://localhost:8000/metrics)
* Health: [http://localhost:8000/healthz](http://localhost:8000/healthz)

---
## Parameters
Parameters are defined in `.env` file (see `.env_example`) and initialized in `config.py`. Here are definitions 
for some of the key parameters:

| Parameter                    | Type |                                                                                  Explanation |
|------------------------------|:----:|---------------------------------------------------------------------------------------------:|
| KNOWLEDGE_BASE_STORAGE_NAME  | str  |    Knowldge base storage type. Supported types: `ChromaKnowledgeBase`, `JsonKVKnowledgeBase` |
| ORDER_API_CLIENT_NAME        | str  | Client type for order API. Supported types: `OrderAPILocalClient`, `OrderAPIBeeceptorClient` |
| ROUTER_NAME                  | str  |            Intent router name. Supported types: `IntentMLRouter`, `LLMRouter`, `NaiveRouter` |

## Architecture (Multi‑Agent Orchestration)

![Architecture](images/workflow.png "architecture")

### Multi‑Turn State & Context

* **State schema** (per `session_id`):

  ```json
  {
    "session_id": "abc123",
    "history": [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}],
    "last_product_context": "Can you track ORD-4567?",
    "last_order_id": "ORD-4567",
    "created_at": "2025-10-24T17:00:00Z",
    "updated_at": "2025-10-24T17:05:00Z"
  }
  ```
* The orchestrator and agents **read/write** this dict. Example: if the user says *“Can you track ORD-4567?”* then later says *“Alright, cancel it.”*, the system uses `last_product_context` + `last_order_id` + `history` to infer intent.

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

**Order ID format**: `ORD-XXXX` (four digits). Regex: `ORD-\d{4}`

**Cancellation window**: placed **< 24 hours** ago.

**Tracking**: return discrete status + ETA date from the mock or Beeceptor API.

**Product Info**: lookup from `kb/faq.json` (string search) or enable embeddings (RAG) via `ENABLE_EMBEDDINGS=true`.

---

## Files

* `app.py` — FastAPI app, orchestrator, agents, tools, and session store
* `agent.py` — orchestrator, agents
* `prompts.py` — LLM prompts
* `agent.py` — orchestrator, agents
* `config.py` — input config
* `memory`:
  * `redis_impl.py` — redis implementation or in-memory store
* `kb`:
  * `chroma_impl.py` — ChromaDB vector DB
  * `json_kv_impl.py` - JSON KV DB
  * `faq.json` — sample knowledge base
* `routers`:
  * `intent_ml_router.py` — ML router
  * `llm_router.py` - LLM router
  * `naive_router.py` — rule-based router
* `requirements.txt` — dependencies
* `Dockerfile` — container image
* `docker-compose.yml` — optional Redis + app stack

---

## Tests
* `test/test_chat.py` — unit tests
* `test/evals_policy.py` — policy evals 
