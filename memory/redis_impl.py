import os
import json
from datetime import datetime, timezone
from typing import Any, Dict
import logging

try:
    import redis
except Exception:
    redis = None

from config import UTC, REDIS_URL


class SessionStore:
    def __init__(self):
        self._use_redis = False
        self._r = None
        self.logger = logging.getLogger("app")
        if REDIS_URL and redis is not None:
            try:
                # self._r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
                self._r = redis.Redis(host=REDIS_URL, port=6379, db=0, decode_responses=True)
                # health check
                self._r.ping()
                self._use_redis = True
                self.logger.info("Using Redis session store", extra={"request_id":"-","session_id":"-","agent":"system"})
            except Exception as e:  # fallback
                self.logger.warning(f"Redis unavailable ({e}); using in-memory store", extra={"request_id":"-","session_id":"-","agent":"system"})
                self._mem: Dict[str, Dict[str, Any]] = {}
        else:
            self._mem: Dict[str, Dict[str, Any]] = {}

    def get(self, session_id: str) -> Dict[str, Any]:
        if self._use_redis:
            raw = self._r.get(f"sess:{session_id}")
            if raw:
                return json.loads(raw)
            doc = {"session_id": session_id, "history": [], "created_at": datetime.now(UTC).isoformat()}
            self._r.set(f"sess:{session_id}", json.dumps(doc))
            return doc
        else:
            if session_id not in self._mem:
                self._mem[session_id] = {"session_id": session_id, "history": [], "created_at": datetime.now(UTC).isoformat()}
            return self._mem[session_id]

    def set(self, session_id: str, state: Dict[str, Any]) -> None:
        state["updated_at"] = datetime.now(UTC).isoformat()
        if self._use_redis:
            self._r.set(f"sess:{session_id}", json.dumps(state))
        else:
            self._mem[session_id] = state


if __name__ == '__main__':
    session = SessionStore()