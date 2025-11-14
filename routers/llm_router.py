import os
import sys
import json
from typing import Tuple, Dict, Any
from openai import OpenAI

from routers.naive_router import NaiveRouter
from llm.openai_client import OpenAIClient, IntentResult
from routers import Intent, INTENT_LIST
from config.settings import settings
from prompts import PROMPTS

cfg = settings.openai


class LLMRouter:
    def __init__(self):
        self.client = OpenAIClient()
        self.model = cfg.chat_model
        self.temperature = cfg.temperature

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