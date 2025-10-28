import os
import time
import logging
import json
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

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
        history = state.get("history", [])
        last_order_id = state.get("last_order_id")
        prompt = f"""
You are a context resolver for an e-commerce assistant.

Conversation history:
{json.dumps(history[-5:], indent=2)}

Current message:
\"\"\"{message}\"\"\"

Known entities:
last_order_id: {last_order_id}

Decide if the user is referring to a specific order, typically formatted as YYY-XXXX.
Respond as JSON: {{
  "resolved_order_id": "<ORD-XXXX or null>",
  "confidence": <0-1>,
  "reasoning": "<brief explanation>"
}}
        """
        resp = self.client(
            model=RESOLVER_MODEL,
            input=prompt,
            temperature=0.2
        )
        try:
            data = json.loads(resp.output[0].content[0].text)
        except Exception:
            data = {"resolved_order_id": None, "confidence": 0, "reasoning": "parse_error"}
        return data


if __name__ == '__main__':
    # load_dotenv(dotenv_path=".env", override=False)
    embeedder = OpenAIEmbedder()
    print(embeedder.embed(['Hello world!']))

    # resolver = LLMContextResolver()
    # state = {
    #     'last_order_id': 'ORD-1234',
    #     'history': [
    #     {'user': 'What is the status of ORD-4567?'},
    #     {'system': "Current status for ORD-4567: processing. Estimated delivery: 2025-10-27T08:10:00Z."}
    # ]}
    # print(resolver.resolve_order_id('Cancel it please!', state=state))

