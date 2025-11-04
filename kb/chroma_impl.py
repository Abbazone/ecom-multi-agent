import os
import json
import numpy as np
import chromadb
from chromadb.config import Settings
from typing import List, Dict
import logging

from llm.openai_client import OpenAIClient
from base import BaseKVStorage
from config import (
    USE_OPENAI_EMBEDDINGS,
    CHROMA_DIR,
    CHROMA_COLLECTION,
    KB_TOP_K,
    KB_MIN_SCORE
)


class ChromaKnowledgeBase(BaseKVStorage):
    def __init__(self, path: str = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "faq.json")
        with open(path, "r", encoding="utf-8") as f:
            self.qa: List[Dict[str, str]] = json.load(f)
        self.use_vectors = os.getenv("ENABLE_EMBEDDINGS", "false").lower() == "true"
        self.collection = None
        self.embedder = OpenAIClient() if (self.use_vectors and USE_OPENAI_EMBEDDINGS) else None
        self.logger = logging.getLogger("app")

        if self.use_vectors and self.embedder:
            self.client = chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(allow_reset=True))
            self.collection = self.client.get_or_create_collection(name=CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"})
            self._bootstrap_if_empty()

    def _bootstrap_if_empty(self):
        if self.collection.count() > 0:
            return
        texts = [row["q"].strip() for row in self.qa]
        ids = [f"kb:{i}" for i in range(len(texts))]
        metas = [{"a": self.qa[i]["a"], "q": self.qa[i]["q"]} for i in range(len(texts))]
        embs = self.embedder.embed(texts)
        self.collection.add(ids=ids, embeddings=embs, documents=texts, metadatas=metas)

    def _fallback_search(self, query: str):
        q = query.lower()
        for item in self.qa:
            if item["q"].lower() in q or q in item["q"].lower():
                return item["a"], [{"q": item["q"], "a": item["a"], "similarity": 1.0}]
        return None, []

    def search_with_citations(self, query: str):
        if not self.use_vectors or not self.collection or not self.embedder:
            return self._fallback_search(query)
        qv = self.embedder.embed([query])[0]
        res = self.collection.query(query_embeddings=[qv], n_results=KB_TOP_K, include=["metadatas", "distances", "documents"])
        distances = (res or {}).get("distances", [[]])[0]
        metas = (res or {}).get("metadatas", [[]])[0]
        docs = (res or {}).get("documents", [[]])[0]
        self.logger.info(f'Searched database with query: {query}')
        if not distances:
            return None, []
        sims = [max(0.0, 1.0 - float(d)) for d in distances]
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        citations = [{"q": docs[i], "a": metas[i].get("a"), "similarity": round(sims[i], 4)} for i in range(len(sims))]
        if best_sim < KB_MIN_SCORE:
            return None, citations
        return metas[best_idx].get("a"), citations

    def search(self, query: str):
        return self.search_with_citations(query)[0]


if __name__ == '__main__':
    kb = ChromaKnowledgeBase()
    print(kb.search('headphone'))