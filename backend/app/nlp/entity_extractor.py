"""
Entity extraction:
  - fields   : "A student should have name, email and age" -> [name, email, age]
  - resource : the main "thing" the API manages                -> student
"""
import re
from collections import Counter

from app.nlp.lexicons import ACTION_LEXICON, ACTOR_WORDS, GENERIC_NOUNS, TYPE_LEXICON
from app.nlp.preprocessor import get_nlp

# Words that introduce a list of fields. STRONG cues are trusted; WEAK cues
# ("with", "store", ":") are common in other sentences too, so they need 2+ items.
STRONG_CUE = re.compile(
    r"\b(?:(?:should|must|will|shall|may|can)\s+have|have|has|having|contains?|containing"
    r"|includes?|including|consists?\s+of|comprises?)\b"
    r"|\b(?:fields|attributes|properties|columns)\b\s*(?:are|is|include|includes|like|such\s+as)?\s*:?",
    re.IGNORECASE)
WEAK_CUE = re.compile(r"\bwith\b|\bstores?\b|\bstoring\b|:", re.IGNORECASE)

# The field list stops where a new clause starts
TAIL_END = re.compile(
    r"\s+(?:where|so\s+that|and\s+(?:users?|admins?|it|they|the\s+system|the\s+api)\b"
    r"|for\s+(?:each|every|all)\b|in\s+the\s+(?:database|system)\b)", re.IGNORECASE)
LEAD_IN = re.compile(
    r"^\s*(?:the\s+)?(?:following\s+)?(?:fields|attributes|properties|columns|details|information)?"
    r"\s*(?:such\s+as|like|namely|:)?\s*", re.IGNORECASE)
SPLIT_LIST = re.compile(r",|;|/|&|\band\b|\bor\b", re.IGNORECASE)
JUNK_ITEMS = {"etc", "more", "so on", "others", "other details", "following", "id"}
COMPARISON_WORDS = {"between", "greater", "less", "than", "above", "below", "under",
                    "over", "equal", "more", "before", "after"}
# verbs after which "with ..." really does introduce fields: "add a student with name and email"
CREATE_VERBS = {v for v, intent in ACTION_LEXICON.items() if intent == "CREATE"} | {
    "build", "make", "develop", "design", "generate", "need", "want", "write", "implement"}


def _clean_item(item: str):
    item = item.lower().strip(" .:;")
    item = re.sub(r"^(?:a|an|the|their|its|his|her|some|each)\s+", "", item)
    item = re.sub(r"[^a-z0-9\s_]", "", item).strip()
    words = item.split()
    if not 1 <= len(words) <= 4 or item in JUNK_ITEMS:
        return None
    return "_".join(words)


def _looks_like_action(item: str) -> bool:
    """'delete_books' is an action; 'order_date' is a field although 'order' is also a verb."""
    words = item.split("_")
    return words[-1] not in TYPE_LEXICON and any(
        w in ACTION_LEXICON or w in ("ability", "able", "access") for w in words)


def _last_noun(text: str):
    """Lemma of the last meaningful noun in a piece of text (the subject before the cue)."""
    doc = get_nlp()(text)
    nouns = [t.lemma_.lower() for t in doc
             if t.pos_ in ("NOUN", "PROPN") and t.lemma_.lower() not in GENERIC_NOUNS]
    if nouns:
        return nouns[-1]
    # "An order has ..." - the tagger may call "order" a verb; a short "a/an/the X" is still a noun
    words = [t for t in doc if t.is_alpha]
    if 2 <= len(words) <= 3 and words[0].text.lower() in ("a", "an", "the", "each", "every"):
        return words[-1].lemma_.lower()
    return None


def extract_fields(sentence: str) -> dict:
    """Returns the fields, the noun they belong to, and the rest of the sentence."""
    empty = {"fields": [], "owner": None, "remainder": sentence}

    match, strong = STRONG_CUE.search(sentence), True
    if not match:
        match, strong = WEAK_CUE.search(sentence), False
    if not match:
        return empty

    prefix, tail = sentence[:match.start()], sentence[match.end():]
    end = TAIL_END.search(tail)
    suffix = tail[end.start():] if end else ""
    tail = LEAD_IN.sub("", tail[:end.start()] if end else tail)

    raw_items = [i for i in SPLIT_LIST.split(tail) if i.strip()]
    items = [_clean_item(i) for i in raw_items]
    if not items or None in items:
        return empty

    owner = _last_noun(prefix)
    has_action = any(_looks_like_action(item) for item in items)
    # "Users should have the ability to add students" is NOT a field list
    if has_action and (not strong or owner is None or owner in ACTOR_WORDS):
        return empty
    if not strong:
        item_words = {w for item in items for w in item.split("_")}
        prefix_verbs = {t.lemma_.lower() for t in get_nlp()(prefix)} & set(ACTION_LEXICON)
        if (len(items) < 2 or has_action or item_words & COMPARISON_WORDS
                or any(w.isdigit() for w in item_words) or prefix_verbs - CREATE_VERBS):
            return empty

    fields = list(dict.fromkeys(items))  # remove duplicates, keep order
    # keep the text before the cue only if it holds an operation: "ADD a student with name..."
    prefix_actions = {t.lemma_.lower() for t in get_nlp()(prefix)} & set(ACTION_LEXICON) - {owner}
    remainder = f"{prefix if prefix_actions else ''} {suffix}".strip()
    return {"fields": fields, "owner": owner, "remainder": remainder}


def is_bare_list(sentence: str) -> bool:
    """'Title, author, ISBN, price and availability.' - a reply that is only a list."""
    items = [_clean_item(i) for i in SPLIT_LIST.split(sentence) if i.strip()]
    return (len(items) >= 2 and None not in items
            and all(len(i.split("_")) <= 3 for i in items)
            and not any(map(_looks_like_action, items)))


def bare_list_fields(sentence: str) -> list:
    items = [_clean_item(i) for i in SPLIT_LIST.split(sentence) if i.strip()]
    return list(dict.fromkeys(i for i in items if i))


PATTERN_BONUS = [
    re.compile(r"\b(?:api|system|app|application|service|backend|platform)\s+"
               r"(?:for|to\s+manage|for\s+managing|that\s+manages)\s+(?:an?\s+|the\s+)?(\w+)", re.I),
    re.compile(r"\b(?:each|every)\s+(\w+)", re.I),
    re.compile(r"\b(\w+)\s+(?:management|api|records?)\b", re.I),
]


def extract_resource(text: str, field_names: list, owners: list) -> dict:
    """
    Scores every noun:  +1 each time it is mentioned
                        +3 when it fits a pattern such as "API for ___" or "each ___"
                        +5 when it OWNS a field list ("A ___ should have name, email")
    The highest score wins.
    """
    nlp = get_nlp()
    field_words = {w for f in field_names for w in f.split("_")}
    scores, actor_scores = Counter(), Counter()

    def add(lemma: str, points: int, is_owner: bool = False) -> None:
        if not lemma or lemma in GENERIC_NOUNS or (lemma in field_words and not is_owner
                                                   and lemma not in owners):
            return
        (actor_scores if lemma in ACTOR_WORDS else scores)[lemma] += points

    for token in nlp(text):
        if token.pos_ in ("NOUN", "PROPN") and token.is_alpha:
            add(token.lemma_.lower(), 1)
    for pattern in PATTERN_BONUS:
        for word in pattern.findall(text):
            token = nlp(word)[0]
            if token.pos_ in ("NOUN", "PROPN") and len(word) > 2:
                add(token.lemma_.lower(), 3)
    for owner in owners:
        add(owner, 5, is_owner=True)

    ranked = (scores or actor_scores).most_common()
    if not ranked:
        return {"resource": None, "candidates": []}
    return {"resource": ranked[0][0],
            "candidates": [{"noun": n, "score": s} for n, s in ranked[:3]]}


def pluralize(noun: str) -> str:
    if noun.endswith("y") and noun[-2:-1] not in "aeiou":
        return noun[:-1] + "ies"
    if noun.endswith(("s", "x", "z", "ch", "sh")):
        return noun + "es"
    return noun + "s"