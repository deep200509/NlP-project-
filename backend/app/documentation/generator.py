"""
Documentation generator (the DOCUMENT stage of the agent).

From the API specification it writes:
    README.md      what the project is, how to run and test it
    API.md         every endpoint with parameters, request example, response example, errors, curl command
    openapi.json   the machine-readable OpenAPI description, exported from the generated app itself
"""
import json
import os
import subprocess
import sys

# realistic example values, chosen by field name; the type decides when the name is unknown
EXAMPLE_BY_NAME = {
    "name": "Asha Patel", "title": "Introduction to NLP", "email": "asha@example.com", "age": 21,
    "course": "B.Sc. Artificial Intelligence", "author": "A. Sharma", "isbn": "978-0131873216",
    "price": 499.0, "salary": 45000.0, "department": "Research", "phone": "9876543210",
    "city": "Mumbai", "address": "12 MG Road, Mumbai", "stock": 25, "quantity": 3, "rating": 4.5,
    "status": "active", "category": "Education", "description": "A short description.",
    "availability": True, "publisher": "Pearson", "pages": 320, "country": "India", "gender": "female",
}
EXAMPLE_BY_TYPE = {"string": None, "text": "A longer piece of text.", "integer": 10, "float": 99.5,
                   "boolean": True, "date": "2026-01-15", "datetime": "2026-01-15T10:30:00",
                   "email": "user@example.com"}
TYPE_WORDS = {"string": "text (up to 255 characters)", "text": "long text", "integer": "whole number",
              "float": "decimal number", "boolean": "true or false", "date": "date (YYYY-MM-DD)",
              "datetime": "date and time (ISO 8601)", "email": "email address"}


def example_value(field: dict):
    name, kind = field["name"], field["type"]
    for key in (name, name.split("_")[-1]):
        value = EXAMPLE_BY_NAME.get(key)
        if value is not None and isinstance(value, {"integer": int, "float": float, "boolean": bool}.get(kind, str)):
            if kind != "boolean" and isinstance(value, bool):
                continue
            return value
    fallback = EXAMPLE_BY_TYPE[kind]
    return fallback if fallback is not None else f"Sample {name.replace('_', ' ')}"


def example_body(spec: dict) -> dict:
    return {f["name"]: example_value(f) for f in spec["fields"]}


def _json(value) -> str:
    return "```json\n" + json.dumps(value, indent=2) + "\n```"


def _curl(method: str, url: str, body=None) -> str:
    lines = [f'curl -X {method} "{url}"']
    if body is not None:
        lines += ['  -H "Content-Type: application/json"', f"  -d '{json.dumps(body)}'"]
    return "```bash\n" + " \\\n".join(lines) + "\n```"


def _errors(rows: list) -> list:
    return ["", "Errors:", "", "| Code | When |", "|---|---|"] + [f"| {code} | {when} |" for code, when in rows]


def build_api_docs(spec: dict) -> str:
    resource, plural = spec["resource"], spec["resource_plural"]
    base = "http://127.0.0.1:8001"
    body = example_body(spec)
    saved = {"id": 1, **body}
    unique = [f["name"] for f in spec["fields"] if f.get("unique")]
    first = spec["fields"][0]["name"]

    out = [f"# {spec['project_name']}: API reference", "",
           f"Base URL when run locally: `{base}`", "",
           "Interactive documentation (Swagger UI) is available at `/docs` while the API is running.", "",
           f"## The {resource} object", "", "| Field | Type | Required | Unique | Example |", "|---|---|---|---|---|",
           "| id | whole number | set automatically | yes | 1 |"]
    out += [f"| {f['name']} | {TYPE_WORDS[f['type']]} | {'yes' if f.get('required', True) else 'no'} | "
            f"{'yes' if f.get('unique') else 'no'} | `{json.dumps(example_value(f))}` |" for f in spec["fields"]]
    out += ["", "## Endpoints", "", "| Method | Path | What it does |", "|---|---|---|"]
    out += [f"| {e['method']} | `{e['path']}` | {e['summary']} |" for e in spec["endpoints"]]

    for endpoint in spec["endpoints"]:
        method, path, operation = endpoint["method"], endpoint["path"], endpoint["operation"]
        out += ["", f"### {method} {path}", "", endpoint["summary"] + "."]
        url = base + path.replace("{id}", "1")

        if operation == "create":
            out += ["", "Request body:", "", _json(body), "", "Response `201 Created`:", "", _json(saved)]
            out += _errors([("422", "a field is missing or has the wrong type")] +
                           ([("409", f"another {resource} already has the same {', '.join(unique)}")] if unique else []))
            out += ["", "Try it:", "", _curl("POST", url, body)]
        elif operation == "read_all":
            params = [("skip", "whole number", "how many rows to skip (default 0)"),
                      ("limit", "whole number", "maximum rows to return (default 100, at most 500)")]
            for p in endpoint.get("query_params", []):
                if p["kind"] in ("min", "max", "equals"):
                    words = {"min": "at least", "max": "at most", "equals": "exactly"}[p["kind"]]
                    params.append((p["name"], TYPE_WORDS.get(p["type"], p["type"]), f"only {plural} whose {p['field']} is {words} this value"))
                elif p["kind"] in ("sort_by", "order"):
                    params.append((p["name"], "text", "one of: " + ", ".join(p["allowed"])))
            out += ["", "Query parameters (all optional):", "", "| Name | Type | Meaning |", "|---|---|---|"]
            out += [f"| {n} | {t} | {m} |" for n, t, m in params]
            extra = next((p for p in endpoint.get("query_params", []) if p["kind"] == "sort_by"), None)
            query = f"?limit=10&sort_by={extra['allowed'][-1]}&order=desc" if extra else "?limit=10"
            out += ["", "Response `200 OK`:", "", _json([saved]), "", "Try it:", "", _curl("GET", url + query)]
        elif operation == "search":
            fields = ", ".join(endpoint.get("search_fields", []))
            out += ["", f"Looks for the keyword inside: {fields}. The search ignores upper and lower case.", "",
                    "Query parameters:", "", "| Name | Type | Meaning |", "|---|---|---|", "| q | text | the keyword (required) |",
                    "", "Response `200 OK`:", "", _json([saved])]
            out += _errors([("422", "the keyword is missing")])
            out += ["", "Try it:", "", _curl("GET", f"{url}?q={str(body.get(endpoint.get('search_fields', [first])[0], 'a')).split()[0]}")]
        elif operation == "read_one":
            out += ["", "Response `200 OK`:", "", _json(saved)]
            out += _errors([("404", f"no {resource} has this id")])
            out += ["", "Try it:", "", _curl("GET", url)]
        elif operation == "update":
            change = {first: example_value(spec["fields"][0])}
            out += ["", "Send only the fields you want to change.", "", "Request body:", "", _json(change), "",
                    "Response `200 OK`:", "", _json(saved)]
            out += _errors([("404", f"no {resource} has this id"), ("422", "a field has the wrong type")] +
                           ([("409", f"another {resource} already has the same {', '.join(unique)}")] if unique else []))
            out += ["", "Try it:", "", _curl("PUT", url, change)]
        elif operation == "delete":
            out += ["", "Response `204 No Content` (empty body)."]
            out += _errors([("404", f"no {resource} has this id")])
            out += ["", "Try it:", "", _curl("DELETE", url)]
    return "\n".join(out) + "\n"


def build_readme(spec: dict, requirement: str | None = None) -> str:
    out = [f"# {spec['project_name']}", "",
           "A REST API generated automatically from a natural-language requirement by the AI API Generator.", ""]
    if requirement:
        out += ["## The requirement", "", "> " + requirement.strip().replace("\n", " "), ""]
    out += ["## What is inside", "", "| File | Purpose |", "|---|---|",
            "| `main.py` | the FastAPI application and its routes |",
            "| `models.py` | the SQLAlchemy model (the database table) |",
            "| `schemas.py` | Pydantic schemas that validate requests and shape responses |",
            "| `crud.py` | the functions that read and write the database |",
            "| `database.py` | the database connection (SQLite by default) |",
            "| `tests/test_api.py` | automatic tests for every endpoint |",
            "| `API.md` | the API reference with request and response examples |",
            "| `openapi.json` | the OpenAPI description, importable into Postman or Swagger Editor |",
            "| `spec.json` | the structured specification this project was generated from |", "",
            "## Run it", "", "```", "python -m venv venv", "venv\\Scripts\\activate        (Windows)",
            "pip install -r requirements.txt", "uvicorn main:app --reload --port 8001", "```", "",
            "Then open http://127.0.0.1:8001/docs for the interactive Swagger documentation.", "",
            "## Test it", "", "```", "python -m pytest tests -v", "```", "",
            "The tests use their own database file, so they never touch real data.", "",
            "## Endpoints", "", "| Method | Path | What it does |", "|---|---|---|"]
    out += [f"| {e['method']} | `{e['path']}` | {e['summary']} |" for e in spec["endpoints"]]
    out += ["", "Request and response examples for every endpoint are in [API.md](API.md).", "",
            "## Database", "", f"Table `{spec['table_name']}`: id, " + ", ".join(f["name"] for f in spec["fields"]) + ".", "",
            "SQLite is used by default. To use PostgreSQL, set the `DATABASE_URL` environment variable, for example "
            f"`postgresql+psycopg://user:password@localhost:5432/{spec['slug']}`."]
    if spec.get("auth_required"):
        out += ["", "> The requirement asked for authentication. It is recorded in `spec.json` but not generated in this version."]
    return "\n".join(out) + "\n"


def export_openapi(project_dir) -> dict | None:
    """Asks the generated app itself for its OpenAPI description (in a separate process, with a time limit)."""
    code = "import json, main; print(json.dumps(main.app.openapi()))"
    scratch = project_dir / "docs_tmp.db"
    try:
        process = subprocess.run([sys.executable, "-c", code], cwd=project_dir, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=60,
                                 env={**os.environ, "DATABASE_URL": "sqlite:///./docs_tmp.db"})
        return json.loads(process.stdout) if process.returncode == 0 else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None
    finally:
        try:
            scratch.unlink(missing_ok=True)
        except PermissionError:
            pass


def write_documentation(project_dir, spec: dict, requirement: str | None = None) -> dict:
    written = {"README.md": build_readme(spec, requirement), "API.md": build_api_docs(spec)}
    openapi = export_openapi(project_dir)
    if openapi is not None:
        written["openapi.json"] = json.dumps(openapi, indent=2)
    for name, content in written.items():
        (project_dir / name).write_text(content, encoding="utf-8")
    return {"files": list(written), "openapi_exported": openapi is not None}