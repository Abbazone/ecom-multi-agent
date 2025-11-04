from __future__ import annotations
from typing import Any


PROMPTS: dict[str, Any] = {}


PROMPTS['router_prompt'] = """
Message: {text}
Rules: If the user mentions cancel/refund → order_cancellation; track/status/ETA → order_tracking; otherwise product_qa.
"""

PROMPTS['context_resolver'] = """
You are a context resolver for an e-commerce assistant.

Conversation history:
{history}

Current message:
\"\"\"{message}\"\"\"

Known entities:
last_order_id: {last_order_id}
last_product_context: {last_product_context}

Decide if the user is referring to a specific order, typically formatted as YYY-XXXX.
Respond as JSON: {{
  "id": "<ORD-XXXX or ABC-XXXX or null>",
  "confidence": <0-1>,
  "reasoning": "<brief explanation>"
}}
"""

if __name__ == '__main__':
    print(PROMPTS['context_resolver'].format(history='a', message='b', last_order_id='c'))
