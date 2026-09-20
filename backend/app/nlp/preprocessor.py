"""
Text preprocessing: raw sentence -> clean tokens the classifier can learn from.

Steps: lowercase -> number normalisation -> remove punctuation
       -> tokenization -> lemmatization -> stop-word removal
"""
import re
from functools import lru_cache

import spacy

from app.config import SPACY_MODEL

# A CUSTOM stop-word list. Standard lists also remove words such as
# "all", "by", "under", "in", "out" - but those carry meaning for us:
# "show ALL books" (READ), "books UNDER 500" (FILTER), "log IN" (AUTH).
STOP_WORDS = {
    "a", "an", "the", "please", "i", "we", "me", "my", "our", "it", "its",
    "this", "that", "to", "of", "for", "and", "also", "be", "is", "are",
    "should", "would", "must", "will", "can", "could", "want", "need",
    "like", "able", "allow", "let", "have", "has", "system", "user",
}


@lru_cache(maxsize=1)
def get_nlp():
    """Load the spaCy model once and reuse it (loading takes a few seconds)."""
    return spacy.load(SPACY_MODEL)


def preprocess(text: str) -> dict:
    """Return every intermediate step, so the pipeline can be shown in a demo."""
    lowered = text.lower().strip()
    # every number becomes the word "num": "under 500" and "under 9000" now look the same
    normalized = re.sub(r"\d+(\.\d+)?", " num ", lowered)
    normalized = re.sub(r"[^a-z\s]", " ", normalized)     # drop punctuation/symbols
    normalized = re.sub(r"\s+", " ", normalized).strip()

    doc = get_nlp()(normalized)
    tokens = [t.text for t in doc if not t.is_space]
    lemmas = [t.lemma_.lower() for t in doc if not t.is_space]
    kept = [w for w in lemmas if w not in STOP_WORDS and len(w) > 1]

    return {
        "original": text,
        "normalized": normalized,
        "tokens": tokens,
        "lemmas": lemmas,
        "without_stop_words": kept,
        "cleaned": " ".join(kept),
    } 