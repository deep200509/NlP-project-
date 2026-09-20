"""
Specification validator: the safety gate before code generation.
errors   -> the specification must NOT be turned into code
warnings -> code can be generated, but the user should look at these points
"""
import keyword
import re

VALID_TYPES = {"string", "text", "integer", "float", "boolean", "date", "datetime", "email"}
VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
PATH = re.compile(r"^/[a-z0-9_]+(?:/(?:[a-z0-9_]+|\{id\}))*$")


def validate_spec(spec: dict) -> dict:
    errors, warnings = [], list(spec.get("warnings", []))

    # 1. resource
    for key in ("resource", "resource_plural", "table_name"):
        value = spec.get(key) or ""
        if not IDENTIFIER.match(value) or keyword.iskeyword(value):
            errors.append(f"'{key}' must be a lowercase identifier, got '{value}'.")

    # 2. fields
    fields = spec.get("fields", [])
    if not fields:
        errors.append("The specification has no fields.")
    seen = set()
    for field in fields:
        name = field.get("name", "")
        if not IDENTIFIER.match(name) or keyword.iskeyword(name):
            errors.append(f"Field name '{name}' is not a valid identifier.")
        if name == "id":
            errors.append("'id' is generated automatically and cannot be a user field.")
        if name in seen:
            errors.append(f"Field '{name}' appears twice.")
        seen.add(name)
        if field.get("type") not in VALID_TYPES:
            errors.append(f"Field '{name}' has unknown type '{field.get('type')}'.")
        if field.get("unique") and field.get("type") in ("text", "boolean", "float"):
            warnings.append(f"Field '{name}' is unique but has type {field['type']}; is that intended?")

    # 3. endpoints
    endpoints = spec.get("endpoints", [])
    if not endpoints:
        errors.append("The specification has no endpoints.")
    routes = set()
    for endpoint in endpoints:
        method, path = endpoint.get("method"), endpoint.get("path", "")
        if method not in VALID_METHODS:
            errors.append(f"Unknown HTTP method '{method}'.")
        if not PATH.match(path):
            errors.append(f"Path '{path}' is not valid.")
        if (method, path) in routes:
            errors.append(f"Endpoint {method} {path} is defined twice.")
        routes.add((method, path))
        for param in endpoint.get("query_params", []):
            if "field" in param and param["field"] not in seen:
                errors.append(f"Query parameter '{param['name']}' refers to unknown field '{param['field']}'.")
        for name in endpoint.get("search_fields", []):
            if name not in seen:
                errors.append(f"Search refers to unknown field '{name}'.")
        if endpoint.get("operation") == "search" and not endpoint.get("search_fields"):
            errors.append("Search was requested but there is no text field to search in.")

    # 4. consistency between operations and endpoints
    produced = {e.get("operation") for e in endpoints}
    expected = {"create": "create", "update": "update", "delete": "delete", "search": "search", "read": "read_all"}
    for operation, endpoint_operation in expected.items():
        if operation in spec.get("operations", []) and endpoint_operation not in produced:
            errors.append(f"Operation '{operation}' has no endpoint.")
    if "create" not in produced:
        warnings.append("There is no create endpoint; the API could never receive data.")
    if "read_all" not in produced and "read_one" not in produced:
        warnings.append("There is no read endpoint; created data could never be viewed.")

    return {"valid": not errors, "errors": errors, "warnings": list(dict.fromkeys(warnings))}