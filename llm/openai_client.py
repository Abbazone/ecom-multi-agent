import os
import time
import logging
import json
from typing import List, Optional
from openai import OpenAI
from pydantic import BaseModel, Field

from prompts import PROMPTS
from routers import INTENT_LIST
from config.settings import settings

openai_cfg = settings.openai


class ResolvedOrder(BaseModel):
    id: Optional[str] = None
    confidence: float = 0.0
    reasoning: Optional[str] = None
    err: Optional[str] = None


class IntentResult(BaseModel):
    intent: Optional[str] = None
    confidence: float = 0.0
    rationale: Optional[str] = None
    err: Optional[str] = None


class OpenAIClient:
    def __init__(self):
        # self.client = completion_with_backoff
        self.client = OpenAI(api_key=openai_cfg.api_key)
        self.logger = logging.getLogger("app")

    def embed(self, texts: List[str]) -> List[List[float]]:
        delay = openai_cfg.backoff_factor
        last_exc = None
        for attempt in range(1, openai_cfg.max_retries + 1):
            try:
                resp = self.client.embeddings.create(model=openai_cfg.embedding_model, input=texts, timeout=openai_cfg.request_timeout_seconds)
                return [d.embedding for d in resp.data]
            except Exception as e:
                last_exc = e
                self.logger.warning(f"Embedding attempt {attempt} failed: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2
        self.logger.error(f"All {openai_cfg.max_retries} embedding attempts failed: {last_exc}")
        raise last_exc

    def resolve_order_id(self, message: str, state: dict) -> ResolvedOrder:
        """Return {resolved_order_id, confidence, reasoning}"""
        history = state.get("history", [])[-5:]
        last_order_id = state.get("last_order_id")
        last_product_context = state.get("last_product_context")
        prompt = PROMPTS['context_resolver'].format(
            history=json.dumps(history, indent=2),
            last_order_id=last_order_id,
            last_product_context=last_product_context,
            message=message,
        )
        delay = openai_cfg.backoff_factor
        last_exc = None
        for attempt in range(1, openai_cfg.max_retries + 1):
            try:
                resp = self.client.responses.create(
                    model=openai_cfg.chat_model,
                    input=prompt,
                    temperature=0.0
                )
                raw = resp.output[0].content[0].text
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as json_decode_error:
                    self.logger.error(f'Context Resolver JSON Decode Error: {json_decode_error}')
                resolved_order = ResolvedOrder.model_validate(data)
                return resolved_order
            except Exception as e:
                last_exc = e
                self.logger.warning(f"LLM resolver attempt {attempt} failed: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2
        self.logger.error(f"All {openai_cfg.max_retries} LLM attempts failed: {last_exc}")

        return ResolvedOrder(err=last_exc)

    def route(self, text: str) -> IntentResult:
        sys = (
            "You are an intent router. Classify the user message into exactly one of: "
            "order_cancellation | order_tracking | product_qa. "
            "Return strict JSON: {intent: string, confidence: number, rationale: string}."
        )
        prompt = PROMPTS['router_prompt'].format(text=text)
        delay = openai_cfg.backoff_factor
        last_exc = None
        for attempt in range(1, openai_cfg.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=openai_cfg.chat_model,
                    temperature=0.0,
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
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as json_decode_error:
                    self.logger.error(f'LLM Router JSON Decode Error: {json_decode_error}')

                intent_result = IntentResult.model_validate(data)
                return intent_result
            except Exception as e:
                last_exc = e
                self.logger.warning(f"LLM router attempt {attempt} failed: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2
        self.logger.error(f"All {openai_cfg.max_retries} LLM attempts failed: {last_exc}")
        return IntentResult(err=str(last_exc))
