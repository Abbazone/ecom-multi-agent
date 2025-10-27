import json
from typing import Optional

from base import (
    BaseKVStorage,
)


class JsonKVKnowledgeBase(BaseKVStorage):
    def __init__(self, path: str = "kb/faq.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.qa = json.load(f)
        except Exception:
            # fallback sample
            self.qa = [
                {"q": "return policy", "a": "You can return items within 30 days in original condition."},
                {"q": "bluetooth headphones battery", "a": "Our BT headphones last up to 30 hours per charge."},
                {"q": "shipping times", "a": "Standard shipping takes 3–5 business days; expedited options available."}
            ]

    def search(self, query: str) -> Optional[str]:
        q = query.lower()
        # simple contains search; pluggable RAG can be added here
        best = None
        for item in self.qa:
            if item["q"] in q or q in item["q"]:
                best = item["a"]
                break
        return best
