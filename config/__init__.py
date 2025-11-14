import re
from datetime import timezone
import os

UTC = timezone.utc
ORDER_ID_RE = re.compile(r"ORD-\d{4}")
REDIS_URL = os.getenv("REDIS_URL")