import re
import os
from datetime import timezone
from dotenv import load_dotenv

load_dotenv()

# agents
# agents.py
UTC = timezone.utc
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ORDER_ID_RE = re.compile(r"ORD-\d{4}")
REDIS_URL = os.getenv("REDIS_URL")
BEECEPTOR_BASE = os.getenv("BEECEPTOR_BASE_URL", "https://ecom-mock.free.beeceptor.com").rstrip("/")
ENABLE_EMBEDDINGS = os.getenv("ENABLE_EMBEDDINGS", "false").lower() == "true"
ROUTER_MODE = os.getenv("ROUTER_MODE", "naive").lower()
RESOLVER_MIN_CONF = float(os.getenv("RESOLVER_MIN_CONF", 0.6))

KNOWLEDGE_BASE_STORAGE_NAME = os.getenv('KNOWLEDGE_BASE_STORAGE_NAME', 'JsonKVKnowledgeBase')
ORDER_API_CLIENT_NAME = os.getenv('ORDER_API_CLIENT_NAME', 'OrderAPILocalClient')
ROUTER_NAME = os.getenv('ROUTER_NAME', 'NaiveRouter')

# kbs
# chroma_impl.py
USE_OPENAI_EMBEDDINGS = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"
CHROMA_DIR = os.getenv("CHROMA_DIR", ".chroma")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "kb_faq")
KB_TOP_K = int(os.getenv("KB_TOP_K", "3"))
KB_MIN_SCORE = float(os.getenv("KB_MIN_SCORE", "0.35"))

# apis
BEECEPTOR_BASE = os.getenv("BEECEPTOR_BASE_URL", "https://ecom-mock.free.beeceptor.com").rstrip("/")
HTTPX_TIMEOUT = float(os.getenv("HTTPX_TIMEOUT", "5.0"))
HTTPX_MAX_RETRIES = int(os.getenv("HTTPX_MAX_RETRIES", "3"))
HTTPX_BACKOFF_FACTOR = float(os.getenv("HTTPX_BACKOFF_FACTOR", "0.5"))

# llm
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "15"))
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
OPENAI_BACKOFF = float(os.getenv("OPENAI_BACKOFF_FACTOR", "0.5"))
RESOLVER_MODEL = os.getenv("RESOLVER_MODEL", "gpt-4o-mini")

# routers
# llm_router.py
ROUTER_LLM_MODEL = os.getenv("ROUTER_LLM_MODEL", "gpt-4o-mini")
ROUTER_LLM_TEMPERATURE = float(os.getenv("ROUTER_LLM_TEMPERATURE", "0.0"))

