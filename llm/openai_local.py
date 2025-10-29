import os
import time
import logging
import json
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

from prompts import PROMPTS
from utils import completion_with_backoff, embedding_with_backoff
from config import (
    OPENAI_EMBED_MODEL,
    OPENAI_TIMEOUT,
    OPENAI_MAX_RETRIES,
    OPENAI_BACKOFF,
    RESOLVER_MODEL
)


class OpenAIEmbedder:
    def __init__(self):
        base = os.getenv("OPENAI_BASE")
        self.client = embedding_with_backoff
        self.logger = logging.getLogger("app")

    def embed(self, texts: List[str]) -> List[List[float]]:
        delay = OPENAI_BACKOFF
        last_exc = None
        for attempt in range(1, OPENAI_MAX_RETRIES + 1):
            try:
                resp = self.client(model=OPENAI_EMBED_MODEL, input=texts, timeout=OPENAI_TIMEOUT)
                return [d.embedding for d in resp.data]
            except Exception as e:
                last_exc = e
                self.logger.warning(f"Embedding attempt {attempt} failed: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2
        self.logger.error(f"All {OPENAI_MAX_RETRIES} embedding attempts failed: {last_exc}")
        raise last_exc


class LLMContextResolver:
    def __init__(self):
        self.client = completion_with_backoff
        self.logger = logging.getLogger("app")

    def resolve_order_id(self, message: str, state: dict) -> dict:
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
        delay = OPENAI_BACKOFF
        last_exc = None
        for attempt in range(1, OPENAI_MAX_RETRIES + 1):
            try:
                resp = self.client(
                    model=RESOLVER_MODEL,
                    input=prompt,
                    temperature=0.0
                )
                data = json.loads(resp.output[0].content[0].text)
                return data
            except Exception as e:
                last_exc = e
                self.logger.warning(f"LLM resolver attempt {attempt} failed: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2
            self.logger.error(f"All {OPENAI_MAX_RETRIES} LLM attempts failed: {last_exc}")
            data = {"resolved_order_id": None, "confidence": 0, "reasoning": f'resolver error {last_exc}'}
        return data
