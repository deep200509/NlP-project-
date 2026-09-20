"""
Data type inference: field name -> data type, in three tiers.
  1. lexicon     exact knowledge             price         -> float
  2. pattern     naming conventions          is_active     -> boolean
  3. similarity  word vectors (semantics)    wage ~ salary -> float
If nothing matches, the safe default is string.
"""
from functools import lru_cache

import numpy as np

from app.nlp.lexicons import TYPE_LEXICON, TYPE_PROTOTYPES
from app.nlp.preprocessor import get_nlp

SIMILARITY_THRESHOLD = 0.60


def _vector(word: str):
    lexeme = get_nlp().vocab[word]
    return lexeme.vector if lexeme.has_vector else None


def cosine(a, b) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


@lru_cache(maxsize=1)
def _prototype_vectors() -> dict:
    return {t: [v for v in map(_vector, words) if v is not None]
            for t, words in TYPE_PROTOTYPES.items()}


def _by_pattern(name: str):
    if name.endswith("_id"):
        return "integer"
    if name.startswith(("is_", "has_")):
        return "boolean"
    if name.endswith("_at"):
        return "datetime"
    if name.startswith("date_of_") or name.endswith("_date"):
        return "date"
    if name.startswith(("number_of_", "no_of_", "num_")) or name.endswith("_count"):
        return "integer"
    return None


def infer_type(field_name: str) -> dict:
    words = field_name.split("_")

    # tier 1a: the whole name is known
    if field_name in TYPE_LEXICON:
        return {"type": TYPE_LEXICON[field_name], "source": "lexicon"}
    # tier 2: naming patterns
    pattern_type = _by_pattern(field_name)
    if pattern_type:
        return {"type": pattern_type, "source": "pattern"}
    # tier 1b: a known word inside the name; the LAST word matters most (phone_number, unit_price)
    for word in reversed(words):
        if word in TYPE_LEXICON:
            return {"type": TYPE_LEXICON[word], "source": "lexicon"}

    # tier 3: semantic similarity between the main word and each type's anchor words
    vector = _vector(words[-1])
    if vector is not None:
        best_type, best_score = None, 0.0
        for type_name, prototypes in _prototype_vectors().items():
            score = max((cosine(vector, p) for p in prototypes), default=0.0)
            if score > best_score:
                best_type, best_score = type_name, score
        if best_type and best_score >= SIMILARITY_THRESHOLD:
            return {"type": best_type, "source": "similarity", "score": round(best_score, 3)}

    return {"type": "string", "source": "default"}