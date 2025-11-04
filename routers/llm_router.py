import os
import sys
import json
from typing import Tuple, Dict, Any
from openai import OpenAI

from routers.naive_router import NaiveRouter
from routers import Intent, INTENT_LIST
from config import (
    ROUTER_LLM_MODEL,
    ROUTER_LLM_TEMPERATURE,
    OPENAI_MAX_RETRIES
)
from prompts import PROMPTS


class LLMRouter:
    def __init__(self):
        self.client = OpenAI()
        self.model = ROUTER_LLM_MODEL
        self.temperature = ROUTER_LLM_TEMPERATURE

    def route(self, text: str) -> Tuple[Intent, float, Dict[str, Any]]:
        sys = (
            "You are an intent router. Classify the user message into exactly one of: "
            "order_cancellation | order_tracking | product_qa. "
            "Return strict JSON: {intent: string, confidence: number, rationale: string}."
        )
        prompt = PROMPTS['router_prompt'].format(text=text)
        for attempt in range(1, OPENAI_MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": sys},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "intent_schema",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "intent": {
                                        "type": "string",
                                        "enum": INTENT_LIST
                                    }
                                },
                                "required": ["intent"],
                                "additionalProperties": False
                            },
                        },
                    },
                )
                content = resp.choices[0].message.content
                data = json.loads(content)
                intent = data.get("intent", "product_qa")
                conf = float(data.get("confidence", 0.0))
                return intent, conf, {"rationale": data.get("rationale", "")}
            except Exception as e:
                # Fallback to naive on parsing errors
                nr = NaiveRouter()
                intent, conf, meta = nr.route(text)
                meta.update({"llm_error": str(e)})
                return intent, conf, meta


if __name__ == "__main__":
    llm = LLMRouter()
    print(llm.route('I want to cancel my order please!'))