"""
Specification generator: structured requirement (Phase 3) -> API specification.

The specification is the single source of truth for everything that follows:
the code generator, the database generator, the tests and the documentation
all read THIS document and never look at the user's original text again.
"""
import keyword
import re

NUMERIC_TYPES = {"integer", "float"}
RANGE_TYPES = {"integer", "float", "date", "datetime"}
TEXT_TYPES = {"string", "text", "email"}

# Names that would break the generated Python / SQLAlchemy / Pydantic code
RESERVED_NAMES = set(keyword.kwlist) | {
    "id", "metadata", "registry", "schema", "json", "dict", "copy", "validate",
    "construct", "fields", "model_config", "model_fields", "query", "session",
}


def safe_field_name(name: str, resource: str) -> tuple[str, bool]:
    """Returns (safe_name, was_renamed). 'class' -> 'student_class', '2nd name' -> 'f_2nd_name'."""
    clean = re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")
    clean = re.sub(r"_+", "_", clean) or "field"
    if clean[0].isdigit():
        clean = f"f_{clean}"
    if clean in RESERVED_NAMES or clean.startswith("model_"):
        clean = f"{resource}_{clean}"
    return clean, clean != name


def apply_constraints(fields: list, constraints: list) -> None:
    """'Email must be unique.' -> email.unique = True   (very small rule-based parser)"""
    for sentence in constraints:
        lowered = sentence.lower()
        for field in fields:
            if not re.search(rf"\b{re.escape(field['name'].replace('_', ' '))}\b", lowered):
                continue
            if "unique" in lowered:
                field["unique"] = True
            if "optional" in lowered:
                field["required"] = False
            if re.search(r"\b(?:required|mandatory|cannot be empty|not be empty)\b", lowered):
                field["required"] = True


def _mentioned_fields(details: list, intent: str, field_names: set) -> tuple[list, list]:
    """Fields named after 'by' for one intent: (known_fields, unknown_words)."""
    known, unknown = [], []
    for detail in details:
        if detail["intent"] == intent:
            for name in detail.get("by", []):
                (known if name in field_names else unknown).append(name)
    return list(dict.fromkeys(known)), list(dict.fromkeys(unknown))


def build_spec(analysis: dict) -> dict:
    resource, plural = analysis["resource"], analysis["resource_plural"]
    operations = analysis["operations"]
    details = analysis["trace"]["operation_details"]
    warnings = []

    # ---- fields ----------------------------------------------------------
    fields = []
    for item in analysis["fields"]:
        name, renamed = safe_field_name(item["name"], resource)
        if renamed:
            warnings.append(f"Field '{item['name']}' was renamed to '{name}' (reserved or invalid name).")
        if item["source"] in ("similarity", "default"):
            warnings.append(f"Type of '{name}' was guessed as {item['type']} ({item['source']}); please confirm.")
        fields.append({"name": name, "type": item["type"], "required": True,
                       "unique": False, "type_source": item["source"]})
    apply_constraints(fields, analysis.get("constraints", []))
    field_names = {f["name"] for f in fields}

    # ---- query parameters of the list endpoint (filter + sort) -----------
    query_params = []
    if "filter" in operations:
        chosen, unknown = _mentioned_fields(details, "FILTER", field_names)
        warnings += [f"Cannot filter by '{u}': it is not a field." for u in unknown]
        for field in fields:
            if chosen and field["name"] not in chosen:
                continue
            if not chosen and field["type"] == "text":
                continue
            if field["type"] in RANGE_TYPES:
                query_params.append({"name": f"min_{field['name']}", "field": field["name"], "kind": "min", "type": field["type"]})
                query_params.append({"name": f"max_{field['name']}", "field": field["name"], "kind": "max", "type": field["type"]})
            else:
                query_params.append({"name": field["name"], "field": field["name"], "kind": "equals", "type": field["type"]})
    if "sort" in operations:
        chosen, unknown = _mentioned_fields(details, "SORT", field_names)
        warnings += [f"Cannot sort by '{u}': it is not a field." for u in unknown]
        sortable = chosen or [f["name"] for f in fields]
        query_params.append({"name": "sort_by", "kind": "sort_by", "type": "string", "allowed": ["id"] + sortable})
        query_params.append({"name": "order", "kind": "order", "type": "string", "allowed": ["asc", "desc"]})

    # ---- endpoints ---------------------------------------------------------
    endpoints = []

    def add(method, path, operation, summary, **extra):
        endpoints.append({"method": method, "path": path, "operation": operation, "summary": summary, **extra})

    if "create" in operations:
        add("POST", f"/{plural}", "create", f"Create a new {resource}")
    if {"read", "filter", "sort"} & set(operations):
        add("GET", f"/{plural}", "read_all", f"List all {plural}", query_params=query_params)
    if "search" in operations:
        chosen, unknown = _mentioned_fields(details, "SEARCH", field_names)
        warnings += [f"Cannot search by '{u}': it is not a field." for u in unknown]
        searchable = [f["name"] for f in fields if f["type"] in TEXT_TYPES and (not chosen or f["name"] in chosen)]
        # declared BEFORE /{id}, otherwise "search" would be read as an id
        add("GET", f"/{plural}/search", "search", f"Search {plural} by keyword",
            query_params=[{"name": "q", "kind": "keyword", "type": "string"}], search_fields=searchable)
    if "read" in operations:
        add("GET", f"/{plural}/{{id}}", "read_one", f"Get one {resource} by id")
    if "update" in operations:
        add("PUT", f"/{plural}/{{id}}", "update", f"Update a {resource}")
    if "delete" in operations:
        add("DELETE", f"/{plural}/{{id}}", "delete", f"Delete a {resource}")

    if "authentication" in operations:
        warnings.append("Authentication was requested; it is recorded here and generated in a later phase.")

    return {
        "project_name": f"{resource.title()} Management API",
        "slug": f"{resource}_management",
        "resource": resource,
        "resource_plural": plural,
        "model_name": resource.title().replace("_", ""),
        "table_name": plural,
        "fields": fields,
        "operations": operations,
        "endpoints": endpoints,
        "auth_required": "authentication" in operations,
        "assumptions": analysis.get("assumptions", []),
        "warnings": warnings,
    }