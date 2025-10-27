from typing import Literal

INTENT_LIST = ["order_cancellation", "order_tracking", "product_qa"]
Intent = Literal["order_cancellation", "order_tracking", "product_qa"]

ROUTERS = {
    "LLMRouter": "routers.llm_router",
    "NaiveRouter": "routers.naive_router",
    "IntentMLRouter": "routers.intent_ml_router",
}