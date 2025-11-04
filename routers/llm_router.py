import os
import sys
import json
from typing import Tuple, Dict, Any
from openai import OpenAI

from routers.naive_router import NaiveRouter
from llm.openai_client import OpenAIClient, IntentResult
from routers import Intent, INTENT_LIST
from config import (
    ROUTER_LLM_MODEL,
    ROUTER_LLM_TEMPERATURE,
    OPENAI_MAX_RETRIES
)
from prompts import PROMPTS


class LLMRouter:
    def __init__(self):
        self.client = OpenAIClient()
        self.model = ROUTER_LLM_MODEL
        self.temperature = ROUTER_LLM_TEMPERATURE

    def route(self, text: str) -> IntentResult:
        intent_result = self.client.route(text)
        if not intent_result.err:
            return intent_result
        else:
            # Fallback to naive on parsing errors
            nr = NaiveRouter()
            intent, conf, meta = nr.route(text)
            return IntentResult(intent=intent, confidence=conf, rationale='matched', err=f"llm_error: {intent_result.err}")


if __name__ == "__main__":
    llm = LLMRouter()
    print(llm.route('I want to cancel my order please!'))