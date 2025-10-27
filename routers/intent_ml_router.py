from typing import Any, Dict, Tuple
from routers import Intent
import sys

sys.path.append('../ZenDesk')

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.svm import LinearSVC
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.pipeline import Pipeline
except Exception:
    TfidfVectorizer = None
    LinearSVC = None
    Pipeline = None

SEED_DATA = [
    ("please cancel ord-1234", "order_cancellation"),
    ("cancel my order", "order_cancellation"),
    ("refund this order", "order_cancellation"),
    ("track ord-5678", "order_tracking"),
    ("where is my package", "order_tracking"),
    ("what's the eta", "order_tracking"),
    ("return policy", "product_qa"),
    ("bluetooth headphones battery life", "product_qa"),
    ("shipping times", "product_qa"),
]


class IntentMLRouter:
    def __init__(self):
        if not (TfidfVectorizer and LinearSVC and Pipeline):
            raise RuntimeError("scikit‑learn not available; install scikit‑learn or use ROUTER_MODE=naive/llm")
        self.pipe: Pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1,2), min_df=1)),
            ("clf", DecisionTreeClassifier())
            # ("clf", LinearSVC())
        ])
        X = [x for x, y in SEED_DATA]
        y = [y for x, y in SEED_DATA]
        self.pipe.fit(X, y)

    def route(self, text: str) -> Tuple[Intent, float, Dict[str, Any]]:
        pred = self.pipe.predict([text])[0]
        conf = max(self.pipe.predict_proba([text])[0])
        return str(pred), float(conf), {"model": type(self.pipe['clf']).__name__}


if __name__ == '__main__':
    ml_router = IntentMLRouter()
    print(ml_router.route('cancel order?'))