import os
import re
import logging
from dataclasses import asdict
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

from schema import *
from utils import get_storage_class, get_api_class, get_router_class
from llm.openai_local import LLMContextResolver

load_dotenv()

ORDER_ID_RE = re.compile(r"ORD-\d{4}")
REDIS_URL = os.getenv("REDIS_URL")
BEECEPTOR_BASE = os.getenv("BEECEPTOR_BASE_URL", "https://ecom-mock.free.beeceptor.com").rstrip("/")
ENABLE_EMBEDDINGS = os.getenv("ENABLE_EMBEDDINGS", "false").lower() == "true"
UTC = timezone.utc
ROUTER_MODE = os.getenv("ROUTER_MODE", "naive").lower()
RESOLVER_MIN_CONF = float(os.getenv("RESOLVER_MIN_CONF", 0.6))

knowldge_base_storage_name = 'ChromaKnowledgeBase'
order_api_client_name = 'OrderAPIBeeceptorClient' # 'OrderAPILocalClient'  # 'OrderAPIBeeceptorClient'
router_name = 'LLMRouter'

knowldge_base_cls = get_storage_class(knowldge_base_storage_name)
order_api_cls = get_api_class(order_api_client_name)
router_cls = get_router_class(router_name)

kb = knowldge_base_cls()
order_api = order_api_cls()
router = router_cls()


class Agent:
    name = "Agent"

    def __init__(self, state: Dict[str, Any]):
        self.state = state
        self.tool_calls: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("app")

    def log(self, request_id: str, session_id: str, msg: str, level: str = "info"):
        extra = {'extra_data': {"request_id": request_id, "session_id": session_id, "agent": self.name}}
        getattr(self.logger, level)(msg, extra=extra)

    def respond(self, text: str, handover_from: str) -> ChatResponse:
        return ChatResponse(
            response=text,
            agent=self.name,
            tool_calls=[ToolCall(**tc) for tc in self.tool_calls],
            handover=f"{handover_from} → {self.name}",
        )


class OrderCancellationAgent(Agent):
    name = "OrderCancellationAgent"

    def handle(self, request_id: str, session_id: str, message: str) -> ChatResponse:
        order_id = resolve_order_id_from_context(self.state, message)
        if not order_id:
            self.log(request_id, session_id, "Missing order ID; prompting user")
            return self.respond(
                "Sure—I can help cancel your order. Please provide your order ID in the format ORD-1234.",
                "OrchestratorAgent",
            )
        # Validate format
        if not ORDER_ID_RE.match(order_id):
            self.log(request_id, session_id, f"Malformed order_id {order_id}")
            return self.respond("That doesn’t look right. Your order ID should look like ORD-1234.", "OrchestratorAgent")

        order = order_api.get_order(order_id)
        if not order:
            msg = f"I couldn't find {order_id}. Please double‑check the ID."
            self.log(request_id, session_id, msg)
            return self.respond(f"I couldn't find {order_id}. Please double‑check the ID.", "OrchestratorAgent")

        # perform cancellation without tool
        placed_at = datetime.fromisoformat(order["placed_at"]).replace(tzinfo=timezone.utc)  # stored UTC
        if datetime.now(UTC) - placed_at > timedelta(hours=24):
            return self.respond(
                f"⛔️{order_id} was placed more than 24 hours ago and isn’t eligible for cancellation. You can still initiate a return once delivered.",
                "OrchestratorAgent",
            )

        # Perform cancellation via tool
        result = order_api.cancel_order(order_id)
        self.tool_calls.append({
            "tool": "OrderCancellationAPI",
            "input": {"orderId": order_id},
            "result": {'status': asdict(result)}})

        if result.status == "cancelled":
            self.state["last_order_id"] = order_id
            return self.respond(f"✅ Done! {order_id} is cancelled and your payment will be refunded.", "OrchestratorAgent")
        elif result.status == "ineligible":
            return self.respond(f"⛔️{order_id} is ineligible for cancellation (placed > 24h ago).", "OrchestratorAgent")
        else:
            return self.respond(f"❗I couldn’t cancel {order_id}. Please contact support.", "OrchestratorAgent")


class OrderTrackingAgent(Agent):
    name = "OrderTrackingAgent"

    def handle(self, request_id: str, session_id: str, message: str) -> ChatResponse:
        order_id = resolve_order_id_from_context(self.state, message)
        if not order_id:
            return self.respond("I can help track your order. What’s your ID? (e.g., ORD-1234)", "OrchestratorAgent")
        if not ORDER_ID_RE.match(order_id):
            return self.respond("Please provide a valid order ID like ORD-1234.", "OrchestratorAgent")
        result = order_api.track_order(order_id)
        self.tool_calls.append({"tool": "OrderTrackingAPI", "input": {"orderId": order_id}, "result": result})
        if result.get("status") == "not_found":
            return self.respond(f"I couldn't find {order_id}.", "OrchestratorAgent")
        self.state["last_order_id"] = order_id
        return self.respond(
            f"Current status for {order_id}: {result['status']}. Estimated delivery: {result['eta']}.",
            "OrchestratorAgent",
        )


class ProductQAAgent(Agent):
    name = "ProductQAAgent"

    def handle(self, request_id: str, session_id: str, message: str) -> ChatResponse:
        self.state["last_product_context"] = message
        ans = kb.search(message) or (
            "Here’s what I found: our standard return window is 30 days. "
            "Shipping is usually 3–5 business days. For specifics, ask about a product feature."
        )
        return self.respond(ans, "OrchestratorAgent")


class OrchestratorAgent(Agent):
    name = "OrchestratorAgent"

    def __init__(self, state: Dict[str, Any]):
        super().__init__(state)
        self.router = router

    def handle(self, request_id: str, session_id: str, message: str) -> ChatResponse:
        intent, confidence, meta = self.router.route(message)
        self.log(msg=f'Routing message: "{message}" -> {intent}', request_id=request_id, session_id=session_id)

        # Emit a Router tool call for observability
        self.tool_calls.append({
            "tool": "Router",
            "input": {"mode": ROUTER_MODE, "text": message},
            "result": {"intent": intent, "confidence": round(float(confidence), 4), "meta": meta}
        })

        # Call the resolver before routing to prefill last_order_id if message has no explicit ID and contains pronouns
        low = message.lower()
        if not ORDER_ID_RE.search(message) and any(p in low for p in ["it", "that", "this", "same"]):
            res = LLMContextResolver().resolve_order_id(message, self.state)
            if res.get("resolved_order_id") and res.get("confidence", 0) >= RESOLVER_MIN_CONF:
                self.log(msg=f'Resolving order_id from message with resolver"{message}" -> {res["resolved_order_id"]}',
                         request_id=request_id,
                         session_id=session_id)
                self.state["last_order_id"] = res["resolved_order_id"]

            # Emit a resolver call for observability
            self.tool_calls.append({
                "tool": "LLMContextResolver",
                "input": {"text": message, 'history': self.state['history'][-5:]},
                "result": {
                    "resolved_order_id": res['resolved_order_id'],
                    "confidence": res['confidence'],
                    "reasoning": res['reasoning']
                }
            })

        if intent == "order_cancellation":
            agent = OrderCancellationAgent(self.state)
        elif intent == "order_tracking":
            agent = OrderTrackingAgent(self.state)
        else:
            agent = ProductQAAgent(self.state)

        resp = agent.handle(request_id, session_id, message)
        # Append our router call to the child response
        resp.tool_calls = [ToolCall(**tc) for tc in (self.tool_calls + [c.model_dump() for c in resp.tool_calls])]
        resp.handover = f"OrchestratorAgent({ROUTER_MODE}) → {agent.name}"
        return resp


def resolve_order_id_from_context(state: dict, message: str) -> Optional[str]:
    # 1) Check explicit ORD-XXXX
    m = ORDER_ID_RE.search(message)
    if m:
        return m.group(0)

    # 2) Try LLM resolver
    resolver = LLMContextResolver()
    res = resolver.resolve_order_id(message, state)
    if res.get("confidence", 0) >= RESOLVER_MIN_CONF and res.get("resolved_order_id"):
        return res["resolved_order_id"]

    # 3) Fallback to last_order_id
    return state.get("last_order_id")
