"""Loads the trained model and predicts the intent of new text."""
from functools import lru_cache

import joblib

from app.config import INTENT_MODEL_PATH
from app.nlp.preprocessor import preprocess


@lru_cache(maxsize=1)
def _load_model():
    if not INTENT_MODEL_PATH.exists():
        raise FileNotFoundError(
            "Intent model not found. Run: python -m app.nlp.train_intent")
    return joblib.load(INTENT_MODEL_PATH)


def predict_intent(text: str) -> dict:
    steps = preprocess(text)
    model = _load_model()
    probabilities = model.predict_proba([steps["cleaned"]])[0]
    ranked = sorted(zip(model.classes_, probabilities), key=lambda p: p[1], reverse=True)
    return {
        "text": text,
        "cleaned": steps["cleaned"],
        "intent": ranked[0][0],
        "confidence": round(float(ranked[0][1]), 3),
        "top_3": [{"intent": i, "probability": round(float(p), 3)} for i, p in ranked[:3]],
    }