"""
The agent's brain: a slot-filling dialogue manager.

The agent needs three "slots" before it can build an API: resource, fields, operations.
Every user message is analysed by the NLP pipeline and merged into the slots.
Stages:  ANALYZE -> CLARIFY (ask for what is missing) -> PLAN -> VALIDATE -> CONFIRM
         -> GENERATE -> TEST -> DONE          (REPAIR and DOCUMENT arrive in later phases)

This file contains NO database code: state goes in, (new state + reply) comes out.
That makes the agent easy to test and easy to explain.
"""
import re

from app.nlp.entity_extractor import pluralize
from app.nlp.lexicons import CANONICAL_ORDER
from app.nlp.preprocessor import get_nlp
from app.nlp.requirement_analyzer import analyze_requirement
from app.nlp.type_inference import infer_type
from app.specification.generator import build_spec
from app.specification.validator import VALID_TYPES, validate_spec

# how much we trust a guess of the resource: said by the user > owns the fields > object of operations > mentioned
RANK = {"user": 4, "owner": 3, "operation": 2, "mention": 1}

YES = re.compile(r"^\s*(?:yes|yep|yeah|ok|okay|sure|generate|go ahead|build(?: it)?|create it|confirm|proceed|"
                 r"do it|looks? good|correct|perfect)\b", re.IGNORECASE)
ADD_FIELD = re.compile(r"\badd\s+(?:the\s+|a\s+|new\s+)?fields?\s+(.+)$", re.IGNORECASE)
REMOVE_FIELD = re.compile(r"\b(?:remove|delete|drop)\s+(?:the\s+)?fields?\s+(.+)$", re.IGNORECASE)
SET_RESOURCE = re.compile(r"\b(?:change|rename|set)\s+(?:the\s+)?resource(?:\s+name)?\s+to\s+(\w+)"
                          r"|\bresource\s+(?:is|should\s+be)\s+(\w+)", re.IGNORECASE)
SET_TYPE = re.compile(r"\b(?:make|change|set)\s+(\w+)\s+(?:(?:to|as|into)\s+)?(?:an?\s+)?(\w+)\s*$", re.IGNORECASE)
GREETING = re.compile(r"^\s*(?:hi+|hello|hey|namaste|good\s+(?:morning|afternoon|evening)|thanks?|thank\s+you)\b[\s!.,]*$",
                      re.IGNORECASE)
ALL_OPERATIONS = re.compile(r"\b(?:all|everything|every\s+operation|basic|usual|standard)\b", re.IGNORECASE)

QUESTIONS = {
    "resource": "What is the main thing this API should manage? For example: students, books or orders.",
    "fields": "What information should each {resource} contain? For example: name, email and age.",
    "operations": "What should users be able to do with {plural}? For example: add, view, update, delete, search.",
}
HELP = ('Reply "generate" to build and test this API, or tell me what to change. For example: '
        '"add field phone", "remove field age", "make age a float", "change resource to book".')


def new_state() -> dict:
    return {"stage": "ANALYZE", "pending": None, "resource": None, "resource_rank": 0,
            "fields": [], "types": {}, "operations": [], "details": [], "constraints": [], "project_id": None}


def _names(text: str) -> list:
    items = re.split(r",|\band\b|&", text.lower())
    return ["_".join(re.sub(r"[^a-z0-9\s_]", "", i).split()) for i in items if i.strip()]


def _singular(word: str) -> str:
    return get_nlp()(word.lower())[0].lemma_.lower()


def _merge(state: dict, text: str) -> bool:
    """ANALYZE: run the NLP pipeline on one message and merge the findings into the slots."""
    analysis = analyze_requirement(text, expect="fields" if state["pending"] == "fields" else None)
    changed = False

    # "library MANAGEMENT api" makes the analyzer assume CRUD; in a conversation we ask instead of assuming
    details = [d for d in analysis["trace"]["operation_details"] if d["method"] != "assumption"]
    operations = [o for o in analysis["operations"] if o in {d["intent"].lower() for d in details}]

    candidates = analysis["trace"]["resource_candidates"]
    if analysis["resource"]:
        kind = "owner" if candidates[0]["score"] >= 5 else ("operation" if operations else "mention")
        if RANK[kind] > state["resource_rank"]:
            state["resource"], state["resource_rank"], changed = analysis["resource"], RANK[kind], True

    for field in analysis["fields"]:
        if field["name"] not in state["fields"] and field["name"] != state["resource"]:
            state["fields"].append(field["name"])
            changed = True
    for operation in operations:
        if operation not in state["operations"]:
            state["operations"].append(operation)
            changed = True
    if state["pending"] == "operations" and not operations and ALL_OPERATIONS.search(text):
        state["operations"] += [o for o in ("create", "read", "update", "delete") if o not in state["operations"]]
        changed = True
    state["details"] += details
    state["constraints"] += [c for c in analysis["constraints"] if c not in state["constraints"]]
    return changed


def _edit(state: dict, text: str) -> str | None:
    """Direct commands while the user reviews the proposal. Returns a note, or None if it was not a command."""
    match = SET_RESOURCE.search(text)
    if match:
        state["resource"], state["resource_rank"] = _singular(match.group(1) or match.group(2)), RANK["user"]
        return f"The resource is now '{state['resource']}'."
    match = ADD_FIELD.search(text)
    if match:
        added = [n for n in _names(match.group(1)) if n and n not in state["fields"]]
        state["fields"] += added
        return f"Added: {', '.join(added)}." if added else "Those fields already exist."
    match = REMOVE_FIELD.search(text)
    if match:
        removed = [n for n in _names(match.group(1)) if n in state["fields"]]
        state["fields"] = [f for f in state["fields"] if f not in removed]
        return f"Removed: {', '.join(removed)}." if removed else "I could not find that field."
    match = SET_TYPE.search(text)
    if match and match.group(1).lower() in state["fields"]:
        wanted = {"int": "integer", "number": "integer", "decimal": "float", "bool": "boolean",
                  "str": "string"}.get(match.group(2).lower(), match.group(2).lower())
        if wanted in VALID_TYPES:
            state["types"][match.group(1).lower()] = wanted
            return f"'{match.group(1).lower()}' is now {wanted}."
        return f"I do not know the type '{match.group(2)}'. Use one of: {', '.join(sorted(VALID_TYPES))}."
    return None


def build_analysis(state: dict) -> dict:
    """The slots, in the same shape that the requirement analyzer produces."""
    fields = []
    for name in state["fields"]:
        guessed = infer_type(name)
        if name in state["types"]:
            guessed = {"type": state["types"][name], "source": "user"}
        fields.append({"name": name, **guessed})
    return {"resource": state["resource"], "resource_plural": pluralize(state["resource"]),
            "fields": fields, "operations": [o for o in CANONICAL_ORDER if o in state["operations"]],
            "constraints": state["constraints"], "assumptions": [],
            "trace": {"operation_details": state["details"]}}


def _proposal(spec: dict, warnings: list, note: str | None) -> str:
    width = max(len(e["method"]) for e in spec["endpoints"]) + 2
    lines = [note, ""] if note else []
    lines += ["I understand the requirements. Here is the proposed API specification.", "",
              f"Resource: {spec['model_name']}", "", "Fields:"]
    lines += [f"  {f['name']} ({f['type']}{', unique' if f['unique'] else ''}{'' if f['required'] else ', optional'})"
              for f in spec["fields"]]
    lines += ["", "Endpoints:"] + [f"  {e['method']:<{width}}{e['path']}" for e in spec["endpoints"]]
    if warnings:
        lines += ["", "Please check:"] + [f"  - {w}" for w in warnings]
    return "\n".join(lines + ["", HELP])


def handle_message(state: dict, text: str) -> dict:
    """One turn of the conversation. Returns {"state", "reply", "action", "spec"}."""
    state = {**new_state(), **state}
    result = {"state": state, "reply": "", "action": None, "spec": None}
    note = None

    if state["stage"] in ("CONFIRM", "DONE"):
        if state["stage"] == "CONFIRM" and YES.search(text):
            spec = build_spec(build_analysis(state))
            state["stage"] = "GENERATE"
            return {**result, "action": "generate", "spec": spec,
                    "reply": "Generating the API, creating the database and running the tests..."}
        note = _edit(state, text)

    if note is None:
        if state["pending"] == "fields" and "?" in text:
            return {**result, "reply": "I mean the pieces of information to store, such as name, email, price or "
                                       "date. Please list them separated by commas."}
        changed = False if GREETING.match(text) else _merge(state, text)
        if not changed and state["stage"] in ("CONFIRM", "DONE"):
            note = "I did not find anything new in that message, so the specification is unchanged."
        if not changed and state["stage"] == "ANALYZE" and not state["resource"]:
            return {**result, "reply": "Hello! Describe the API you need in plain English, for example: "
                                       '"Create an API for a library. Each book has title, author and price. '
                                       'Users can add, view, update and delete books."'}

    # CLARIFY: ask for the first thing that is still missing, one question at a time
    for slot in ("resource", "fields", "operations"):
        if not state[slot]:
            state["stage"], state["pending"] = "CLARIFY", slot
            resource = state["resource"] or "item"
            result["reply"] = QUESTIONS[slot].format(resource=resource, plural=pluralize(resource))
            return result

    # PLAN + VALIDATE: everything is known, so build the specification and check it
    state["pending"] = None
    spec = build_spec(build_analysis(state))
    report = validate_spec(spec)
    if not report["valid"]:
        state["stage"] = "CLARIFY"
        result["reply"] = "I cannot build this yet:\n" + "\n".join(f"  - {e}" for e in report["errors"])
        return result
    state["stage"] = "CONFIRM"
    return {**result, "spec": spec, "reply": _proposal(spec, report["warnings"], note)}


def result_reply(project_name: str, tests: dict, project_id: int) -> str:
    """What the agent says after GENERATE + TEST."""
    outcome = ("All tests passed." if tests["success"] else
               "Some tests failed. The repair agent (next phase) will try to fix this automatically.")
    return "\n".join([f"{project_name} is ready (project #{project_id}).", "", tests["report"], "", outcome,
                      "", "You can keep chatting to change it, for example: \"add field phone\"."])