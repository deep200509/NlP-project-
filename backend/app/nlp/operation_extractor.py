"""
Operation extraction: finds every operation in a sentence.

"Users should be able to add students, view all students and delete students"
   -> chunk "add students"       -> CREATE
   -> chunk "view all students"  -> READ
   -> chunk "delete students"    -> DELETE

Each chunk's intent is decided by three methods, in this order:
  1. classifier  the ML model from Phase 2 (when it is confident)
  2. lexicon     the chunk contains a known action verb
  3. similarity  word vectors: an unseen verb such as "purge" is close to "delete"
"""
import re
from functools import lru_cache

from app.nlp.intent_classifier import predict_intent
from app.nlp.lexicons import ACTION_LEXICON, INTENT_SEEDS
from app.nlp.preprocessor import get_nlp
from app.nlp.type_inference import cosine

CONFIDENCE_THRESHOLD = 0.55
SIMILARITY_THRESHOLD = 0.55

SPLIT_CHUNKS = re.compile(
    r",|;|\band\b|\bor\b|\bas\s+well\s+as\b|\bthen\b|\bso\s+that\b|\bbefore\s+(?:they|users?)\b",
    re.IGNORECASE)
# "Create an API for ..." talks ABOUT the project; it is not an operation on the resource
META_CLAUSE = re.compile(
    r"\b(?:create|build|make|develop|design|generate|need|want|write|implement)\b[^,;]{0,40}?"
    r"\b(?:apis?|system|application|app|backend|service|platform|project|website|software)\b",
    re.IGNORECASE)
CRUD_WORD = re.compile(r"\bcrud\b|\ball\s+(?:basic\s+)?operations\b", re.IGNORECASE)
BY_PHRASE = re.compile(r"\bby\s+(?:their\s+|its\s+|the\s+)?(.+)$", re.IGNORECASE)
# verbs that never name an operation
HELPER_VERBS = {"be", "have", "do", "should", "can", "want", "need", "allow", "let", "use",
                "able", "like", "manage", "support", "provide", "include", "contain"}


@lru_cache(maxsize=1)
def _seed_vectors() -> dict:
    vocab = get_nlp().vocab
    return {intent: [vocab[v].vector for v in verbs if vocab[v].has_vector]
            for intent, verbs in INTENT_SEEDS.items()}


def similarity_intent(token):
    """Closest intent for a verb the lexicon does not know, using word vectors."""
    if not token.has_vector:
        return None, 0.0
    best_intent, best_score = None, 0.0
    for intent, vectors in _seed_vectors().items():
        score = max((cosine(token.vector, v) for v in vectors), default=0.0)
        if score > best_score:
            best_intent, best_score = intent, score
    if best_score >= SIMILARITY_THRESHOLD:
        return best_intent, round(best_score, 3)
    return None, 0.0


def _find_action(chunk: str):
    """Returns (lexicon_intent, similarity_intent, similarity_score) for one chunk."""
    lexicon_hit, sim_hit, sim_score = None, None, 0.0
    content_seen = False
    for token in get_nlp()(chunk):
        lemma = token.lemma_.lower()
        if not token.is_alpha or lemma in HELPER_VERBS or token.pos_ in ("DET", "PRON", "AUX", "ADP", "PART"):
            continue
        first_content_word = not content_seen and lemma not in ("user", "admin")
        content_seen = content_seen or first_content_word
        if lemma in ACTION_LEXICON and (token.pos_ == "VERB" or first_content_word):
            lexicon_hit = lexicon_hit or ACTION_LEXICON[lemma]
        elif token.pos_ == "VERB" and lemma not in ACTION_LEXICON:
            intent, score = similarity_intent(token)
            if score > sim_score:
                sim_hit, sim_score = intent, score
    return lexicon_hit, sim_hit, sim_score


def _by_fields(chunk: str) -> list:
    match = BY_PHRASE.search(chunk)
    if not match:
        return []
    items = [re.sub(r"[^a-z0-9\s]", "", i.lower()).strip() for i in re.split(r",|\band\b|\bor\b", match.group(1))]
    return ["_".join(i.split()) for i in items if i and len(i.split()) <= 3]


def extract_operations(sentence: str, resource) -> list:
    # 1. cut the sentence into chunks; a chunk without an action verb belongs to the previous one
    chunks = []
    for piece in SPLIT_CHUNKS.split(sentence):
        piece = piece.strip(" .")
        if not piece:
            continue
        action = _find_action(piece)
        if any(action[:2]) or CRUD_WORD.search(piece):
            chunks.append([piece, action])
        elif chunks:
            chunks[-1][0] += f" and {piece}"

    # 2. decide the intent of every chunk
    operations = []
    for text, (lexicon_intent, sim_intent, sim_score) in chunks:
        if CRUD_WORD.search(text):
            for intent in ("CREATE", "READ", "UPDATE", "DELETE"):
                operations.append({"clause": text, "intent": intent, "confidence": 1.0, "method": "keyword"})
            continue
        if META_CLAUSE.search(text):
            continue

        classifier_input = text if not resource or resource in text.lower() else f"{text} {resource}"
        prediction = predict_intent(classifier_input)
        if prediction["confidence"] >= CONFIDENCE_THRESHOLD:
            intent, confidence, method = prediction["intent"], prediction["confidence"], "classifier"
        elif lexicon_intent:
            intent, confidence, method = lexicon_intent, prediction["confidence"], "lexicon"
        elif sim_intent:
            intent, confidence, method = sim_intent, sim_score, "similarity"
        else:
            intent, confidence, method = prediction["intent"], prediction["confidence"], "classifier_low_confidence"

        operation = {"clause": text, "intent": intent, "confidence": confidence, "method": method}
        if intent in ("SEARCH", "FILTER", "SORT") and _by_fields(text):
            operation["by"] = _by_fields(text)
        operations.append(operation)
    return operations