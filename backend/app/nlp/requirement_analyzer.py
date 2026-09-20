"""
Requirement analyzer: natural-language requirement -> structured requirement.
This is the explicit intermediate representation between the user's text
and the API specification (Phase 4).
"""
import re

from app.nlp.entity_extractor import (bare_list_fields, extract_fields, extract_resource,
                                      is_bare_list, pluralize)
from app.nlp.lexicons import CANONICAL_ORDER
from app.nlp.operation_extractor import extract_operations
from app.nlp.preprocessor import get_nlp
from app.nlp.type_inference import infer_type

CONSTRAINT_WORDS = re.compile(
    r"\b(?:unique|required|mandatory|optional|at\s+least|at\s+most|minimum|maximum"
    r"|must\s+be|cannot\s+be|can't\s+be|not\s+be\s+empty)\b", re.IGNORECASE)
MANAGE_WORD = re.compile(r"\bmanag", re.IGNORECASE)


def analyze_requirement(text: str, expect: str | None = None) -> dict:
    """
    expect: optional hint from the agent (later phase).
            "fields" -> the text is an answer to "what fields should it have?"
    """
    sentences = [s.text.strip() for s in get_nlp()(text).sents if s.text.strip()]

    # 1. sentence by sentence: pull out field lists, keep the rest for operations
    field_names, owners, report, leftovers = [], [], [], []
    for sentence in sentences:
        found = extract_fields(sentence)
        if not found["fields"] and (expect == "fields" or is_bare_list(sentence)):
            field_names += bare_list_fields(sentence)
            report.append({"text": sentence, "kind": "field_list"})
            leftovers.append(None)
        elif found["fields"]:
            field_names += found["fields"]
            owners.append(found["owner"])
            report.append({"text": sentence, "kind": "field_definition"})
            leftovers.append(found["remainder"] or None)
        else:
            report.append({"text": sentence, "kind": "description"})
            leftovers.append(sentence)
    field_names = list(dict.fromkeys(field_names))

    # 2. the resource
    found_resource = extract_resource(text, field_names, [o for o in owners if o])
    resource = found_resource["resource"]

    # 3. operations from whatever is left of each sentence
    details = []
    for entry, leftover in zip(report, leftovers):
        if not leftover:
            continue
        operations = extract_operations(leftover, resource)
        details += operations
        if operations and entry["kind"] == "description":
            only_auth = all(o["intent"] == "AUTHENTICATION" for o in operations)
            entry["kind"] = "authentication" if only_auth else "operation"
        elif entry["kind"] == "description" and CONSTRAINT_WORDS.search(entry["text"]):
            entry["kind"] = "constraint"

    assumptions = []
    if not details and MANAGE_WORD.search(text):
        assumptions.append('The text says "manage", so full CRUD was assumed.')
        details = [{"clause": "manage", "intent": i, "confidence": 0.5, "method": "assumption"}
                   for i in ("CREATE", "READ", "UPDATE", "DELETE")]
    if field_names:
        assumptions.append("An integer primary key 'id' is added automatically.")

    found_intents = {d["intent"].lower() for d in details}
    operations = [o for o in CANONICAL_ORDER if o in found_intents]

    # 4. what is still missing? (the agent will turn these into questions)
    missing = [name for name, value in
               (("resource", resource), ("fields", field_names), ("operations", operations)) if not value]

    return {
        "resource": resource,
        "resource_plural": pluralize(resource) if resource else None,
        "fields": [{"name": f, **infer_type(f)} for f in field_names],
        "operations": operations,
        "complete": not missing,
        "missing": missing,
        "assumptions": assumptions,
        "constraints": [e["text"] for e in report if e["kind"] == "constraint"],
        "trace": {
            "sentences": report,
            "resource_candidates": found_resource["candidates"],
            "operation_details": details,
        },
    }