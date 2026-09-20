"""
Test generator: API specification -> tests/test_api.py (pytest + FastAPI TestClient).

Every endpoint in the specification gets at least one test, plus tests for the
error cases (404 unknown id, 422 invalid body, 409 duplicate unique value).
"""
import json


def _sample_expression(field: dict) -> str:
    """Python expression (using n) that produces a valid JSON value for this field."""
    name, kind = field["name"], field["type"]
    return {
        "string": f'f"Sample {name} {{n}}"',
        "text": f'f"Sample {name} text {{n}}"',
        "email": 'f"user{n}@example.com"',
        "integer": "20 + n",
        "float": "100.5 + n",
        "boolean": "n % 2 == 1",
        "date": 'f"2024-01-{10 + n:02d}"',
        "datetime": 'f"2024-01-{10 + n:02d}T10:30:00"',
    }[kind]


def _endpoint(spec: dict, operation: str):
    return next((e for e in spec["endpoints"] if e["operation"] == operation), None)


def generate_tests(spec: dict) -> tuple[str, dict]:
    """Returns (source code of test_api.py, labels used to display the results)."""
    model, resource, plural = spec["model_name"], spec["resource"], spec["resource_plural"]
    base = f"/{plural}"
    fields = spec["fields"]
    produced = {e["operation"] for e in spec["endpoints"]}
    labels = {}

    lines = [
        f'"""Automatic tests for {spec["project_name"]}. Generated from the API specification."""',
        "import datetime as dt",
        "import os",
        "import sys",
        "from pathlib import Path",
        "",
        "# tests ALWAYS use their own database file, never the real one",
        'os.environ["DATABASE_URL"] = "sqlite:///./test_run.db"',
        "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so 'import main' works",
        "",
        "import pytest",
        "from fastapi.testclient import TestClient",
        "",
        "import models",
        "from database import Base, SessionLocal, engine",
        "from main import app",
        "",
        "",
        "@pytest.fixture()",
        "def client():",
        '    """Every test starts with an empty table."""',
        "    Base.metadata.drop_all(bind=engine)",
        "    Base.metadata.create_all(bind=engine)",
        "    with TestClient(app) as test_client:",
        "        yield test_client",
        "",
        "",
        "def sample(n: int = 1) -> dict:",
        f'    """A valid JSON body for one {resource}; n makes every record different."""',
        "    return {",
    ]
    lines += [f'        "{f["name"]}": {_sample_expression(f)},' for f in fields]
    lines += [
        "    }",
        "",
        "",
        "def make_item(n: int = 1, **overrides) -> int:",
        f'    """Puts one {resource} straight into the database and returns its id."""',
        "    data = {**sample(n), **overrides}",
    ]
    for f in fields:
        if f["type"] == "date":
            lines.append(f'    data["{f["name"]}"] = dt.date.fromisoformat(data["{f["name"]}"])')
        elif f["type"] == "datetime":
            lines.append(f'    data["{f["name"]}"] = dt.datetime.fromisoformat(data["{f["name"]}"])')
    lines += [
        "    with SessionLocal() as db:",
        f"        item = models.{model}(**data)",
        "        db.add(item)",
        "        db.commit()",
        "        return item.id",
    ]

    def test(name: str, endpoint: str, check: str, body: list) -> None:
        labels[name] = {"endpoint": endpoint, "check": check}
        lines.extend(["", "", f"def {name}(client):", *[f"    {line}" for line in body]])

    if "create" in produced:
        test("test_create", f"POST {base}", f"creates a {resource}", [
            f'response = client.post("{base}", json=sample())',
            "assert response.status_code == 201, response.text",
            "body = response.json()",
            'assert body["id"] > 0',
            "for key, value in sample().items():",
            "    assert body[key] == value",
        ])
        if any(f.get("required", True) for f in fields):
            test("test_create_rejects_empty_body", f"POST {base}", "rejects a body with missing fields (422)", [
                f'response = client.post("{base}", json={{}})',
                "assert response.status_code == 422, response.text",
            ])
        email = next((f["name"] for f in fields if f["type"] == "email"), None)
        if email:
            test("test_create_rejects_bad_email", f"POST {base}", "rejects an invalid email (422)", [
                f'response = client.post("{base}", json={{**sample(), "{email}": "not-an-email"}})',
                "assert response.status_code == 422, response.text",
            ])
        unique = next((f["name"] for f in fields if f.get("unique")), None)
        if unique:
            test("test_create_rejects_duplicate", f"POST {base}", f"rejects a duplicate {unique} (409)", [
                f'assert client.post("{base}", json=sample()).status_code == 201',
                f'response = client.post("{base}", json=sample())',
                "assert response.status_code == 409, response.text",
            ])

    if "read_all" in produced:
        test("test_read_all", f"GET {base}", f"lists all {plural}", [
            "make_item(1)",
            "make_item(2)",
            f'response = client.get("{base}")',
            "assert response.status_code == 200, response.text",
            "assert len(response.json()) == 2",
        ])
        params = _endpoint(spec, "read_all").get("query_params", [])
        first_filter = next((p for p in params if p["kind"] in ("min", "equals")), None)
        if first_filter:
            field, kind = first_filter["field"], first_filter["type"]
            low, high, middle = {
                "integer": ("10", "1000", "500"), "float": ("10.0", "1000.0", "500"),
                "date": ('"2020-01-01"', '"2024-01-01"', "2022-01-01"),
                "datetime": ('"2020-01-01T00:00:00"', '"2024-01-01T00:00:00"', "2022-01-01T00:00:00"),
                "boolean": ("False", "True", "true"),
                "email": ('"alpha@example.com"', '"beta@example.com"', "beta@example.com"),
            }.get(kind, ('"alpha"', '"beta"', "beta"))
            test("test_filter", f"GET {base}?{first_filter['name']}=", f"filters {plural} by {field}", [
                f"make_item(1, {field}={low})",
                f"make_item(2, {field}={high})",
                f'response = client.get("{base}", params={{"{first_filter["name"]}": "{middle}"}})',
                "assert response.status_code == 200, response.text",
                "assert len(response.json()) == 1",
            ])
        sort = next((p for p in params if p["kind"] == "sort_by"), None)
        if sort:
            column = next((a for a in sort["allowed"] if a != "id"), "id")
            test("test_sort", f"GET {base}?sort_by=", f"sorts {plural} by {column}", [
                "make_item(1)",
                "make_item(2)",
                f'response = client.get("{base}", params={{"sort_by": "{column}", "order": "desc"}})',
                "assert response.status_code == 200, response.text",
                f'values = [row["{column}"] for row in response.json()]',
                "assert values == sorted(values, reverse=True)",
            ])

    if "search" in produced:
        target = _endpoint(spec, "search")["search_fields"][0]
        test("test_search", f"GET {base}/search", f"finds {plural} by keyword", [
            "make_item(1)",
            f'response = client.get("{base}/search", params={{"q": "Sample {target}"}})' if
            next(f for f in fields if f["name"] == target)["type"] != "email" else
            f'response = client.get("{base}/search", params={{"q": "user1"}})',
            "assert response.status_code == 200, response.text",
            "assert len(response.json()) == 1",
        ])

    if "read_one" in produced:
        test("test_read_one", f"GET {base}/{{id}}", f"returns one {resource}", [
            "item_id = make_item()",
            f'response = client.get(f"{base}/{{item_id}}")',
            "assert response.status_code == 200, response.text",
            'assert response.json()["id"] == item_id',
        ])
        test("test_read_one_not_found", f"GET {base}/{{id}}", "unknown id gives 404", [
            f'response = client.get("{base}/999999")',
            "assert response.status_code == 404, response.text",
        ])

    if "update" in produced:
        target = fields[0]
        test("test_update", f"PUT {base}/{{id}}", f"updates a {resource}", [
            "item_id = make_item(1)",
            f'new_value = sample(2)["{target["name"]}"]',
            f'response = client.put(f"{base}/{{item_id}}", json={{"{target["name"]}": new_value}})',
            "assert response.status_code == 200, response.text",
            f'assert response.json()["{target["name"]}"] == new_value',
        ])
        test("test_update_not_found", f"PUT {base}/{{id}}", "unknown id gives 404", [
            f'response = client.put("{base}/999999", json={{}})',
            "assert response.status_code == 404, response.text",
        ])

    if "delete" in produced:
        test("test_delete", f"DELETE {base}/{{id}}", f"deletes a {resource}", [
            "item_id = make_item()",
            f'response = client.delete(f"{base}/{{item_id}}")',
            "assert response.status_code == 204, response.text",
            "with SessionLocal() as db:",
            f"    assert db.get(models.{model}, item_id) is None",
        ])
        test("test_delete_not_found", f"DELETE {base}/{{id}}", "unknown id gives 404", [
            f'response = client.delete("{base}/999999")',
            "assert response.status_code == 404, response.text",
        ])

    return "\n".join(lines) + "\n", labels


def generate_test_files(spec: dict) -> dict:
    source, labels = generate_tests(spec)
    return {"tests/test_api.py": source, "tests/labels.json": json.dumps(labels, indent=2)}