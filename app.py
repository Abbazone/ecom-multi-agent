import os
import json
import time
import logging
import uuid
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY

from config import LOG_LEVEL
from models import ChatResponse, ChatRequest
from agent import OrchestratorAgent
from memory.redis_impl import SessionStore


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "level": record.levelname,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "msg": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "extra_data"):
            base.update(getattr(record, "extra_data"))
        return json.dumps(base)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("app")
logger.setLevel(LOG_LEVEL)
logger.addHandler(handler)
logger.propagate = False

REQUEST_COUNTER: Optional[Counter] = None
REQUEST_LATENCY: Optional[Histogram] = None


def init_metrics(registry=REGISTRY) -> None:
    global REQUEST_COUNTER, REQUEST_LATENCY
    if REQUEST_COUNTER is None:
        REQUEST_COUNTER = Counter(
            "chat_requests_total",
            "Total /chat requests",
            ["agent", "status"],
            registry=registry,
        )
    if REQUEST_LATENCY is None:
        REQUEST_LATENCY = Histogram(
            "chat_request_seconds",
            "Latency of /chat requests in seconds",
            registry=registry,
        )


store = SessionStore()
app = FastAPI(title="E‑commerce Multi‑Agent CS System", version="1.0.0")


@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    init_metrics()
    request_id = str(uuid.uuid4())
    session_id = req.session_id
    start = time.time()

    # Load and update session
    state = store.get(session_id)
    state.setdefault("history", []).append({"role": "user", "content": req.message})

    # Orchestrate
    orch = OrchestratorAgent(state)
    try:
        resp: ChatResponse = orch.handle(request_id, session_id, req.message)
        # Persist state
        store.set(session_id, state)
        # Record in history
        state["history"].append({"role": "assistant", "content": resp.response, "agent": resp.agent})
        # Metrics
        latency = time.time() - start
        REQUEST_COUNTER.labels(agent=resp.agent, status="200").inc()
        REQUEST_LATENCY.observe(latency)
        # Logging
        logger.info(
            "Handled chat",
            extra={"extra_data": {"request_id": request_id, "session_id": session_id, "agent": resp.agent}}
        )
        return JSONResponse(status_code=200, content=json.loads(resp.model_dump_json()))
    except Exception as e:
        REQUEST_COUNTER.labels(agent="error", status="500").inc()
        logger.exception("Chat error",
                         extra={"extra_data": {"request_id": request_id, "session_id": session_id, "agent": "OrchestratorAgent"}})
        return JSONResponse(status_code=500, content={
            "response": "Sorry—something went wrong.",
            "agent": "OrchestratorAgent",
            "tool_calls": [],
            "handover": "OrchestratorAgent",
            "error": str(e),
        })
