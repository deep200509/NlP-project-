"""
Self-repair loop:   run tests -> analyse the error -> ask the LLM for a fix -> CHECK the fix
                    -> apply it -> run the tests again        (at most MAX_ATTEMPTS times)

Rules that keep this safe and honest:
  1. The tests are the judge. The LLM may never edit them.
  2. LLM-written code is untrusted: it must parse, may import only known libraries and may not
     call dangerous functions. Otherwise it is rejected before it ever runs.
  3. A fix that does not make more tests pass is undone, so bad patches never pile up.
  4. The loop always ends: MAX_ATTEMPTS attempts, never more.

This file has no database code; the routes store what happens here.
"""
import ast
import re

from app.code_generator.project_generator import GENERATED_DIR
from app.llm.client import LLMError, generate
from app.testing.runner import run_tests

MAX_ATTEMPTS = 3
EDITABLE_FILES = ("main.py", "crud.py", "schemas.py", "models.py", "database.py")
ALLOWED_IMPORTS = {"fastapi", "sqlalchemy", "pydantic", "typing", "datetime", "crud", "models", "schemas", "database"}
BANNED_CALLS = {"eval", "exec", "compile", "open", "__import__", "input", "breakpoint", "globals", "locals"}

SYSTEM = """You are a careful Python engineer repairing a small FastAPI + SQLAlchemy project.
The automated tests are correct and you cannot change them. Find the bug in the application code.
Change as little as possible. Answer in EXACTLY this format and nothing else:

DIAGNOSIS: <one or two sentences explaining the bug>
FILE: <one file name: main.py, crud.py, schemas.py, models.py or database.py>
```python
<the COMPLETE corrected content of that file>
```"""

ERROR_TYPES = [            # rule-based error analyser: first match wins
    ("syntax_error", r"SyntaxError|IndentationError"),
    ("import_error", r"ImportError|ModuleNotFoundError"),
    ("name_error", r"NameError|AttributeError|UnboundLocalError"),
    ("type_error", r"TypeError"),
    ("database_error", r"sqlalchemy\.exc|OperationalError|IntegrityError"),
    ("wrong_status_code", r"assert \d{3} == \d{3}"),
    ("wrong_result", r"AssertionError|assert "),
]


def analyze_failure(tests: dict) -> dict:
    """ERROR ANALYZER: which tests failed, what kind of error is it, which files look suspicious."""
    failed = [r for r in tests["results"] if r["status"] == "FAIL"]
    evidence = "\n".join(f"{r['message']}\n{r['details']}" for r in failed) + "\n" + tests.get("log_tail", "")
    error_type = next((name for name, pattern in ERROR_TYPES if re.search(pattern, evidence)), "unknown")
    mentioned = re.findall(r"[\\/](main|crud|schemas|models|database)\.py", evidence)
    suspects = list(dict.fromkeys(f"{m}.py" for m in mentioned)) or ["main.py", "crud.py"]
    summary = "; ".join(f"{r['test']}: {r['message'][:120]}" for r in failed) or tests.get("log_tail", "")[-300:]
    return {"error_type": error_type, "suspects": suspects, "summary": summary,
            "failed_tests": [r["test"] for r in failed]}


def _test_source(project_dir, names: list) -> str:
    source = (project_dir / "tests" / "test_api.py").read_text(encoding="utf-8")
    blocks = [m.group(0) for name in names
              for m in [re.search(rf"^def {re.escape(name)}\(.*?(?=^def |\Z)", source, re.M | re.S)] if m]
    return "\n".join(blocks) or source[-1500:]


def build_prompt(project_dir, spec: dict, tests: dict, analysis: dict, history: list) -> str:
    parts = [f"PROJECT: {spec['project_name']}",
             "ENDPOINTS: " + ", ".join(f"{e['method']} {e['path']}" for e in spec["endpoints"]),
             "FIELDS: " + ", ".join(f"{f['name']}:{f['type']}" for f in spec["fields"]),
             f"\nERROR TYPE (from our analyser): {analysis['error_type']}",
             f"SUSPICIOUS FILES: {', '.join(analysis['suspects'])}",
             "\nFAILING TESTS (correct, read-only):\n" + _test_source(project_dir, analysis["failed_tests"]),
             "\nERROR OUTPUT:\n" + "\n".join(f"{r['test']}: {r['message']}\n{r['details'][-600:]}"
                                            for r in tests["results"] if r["status"] == "FAIL")]
    if tests.get("log_tail"):
        parts.append("\nTEST RUNNER LOG (end):\n" + tests["log_tail"][-1500:])
    if history:
        parts.append("\nEARLIER ATTEMPTS THAT DID NOT WORK:\n" + "\n".join(f"- {h}" for h in history))
    for name in EDITABLE_FILES:
        parts.append(f"\n===== {name} =====\n" + (project_dir / name).read_text(encoding="utf-8"))
    return "\n".join(parts)


def parse_answer(answer: str):
    """Returns (diagnosis, file, code) or None when the LLM ignored the format."""
    file_match = re.search(r"^FILE:\s*`?([^\s`]+)`?\s*$", answer, re.M)
    code_match = re.search(r"```(?:python|py)?[ \t]*\n(.*?)```", answer, re.S)
    if not file_match or not code_match:
        return None
    diagnosis = re.search(r"DIAGNOSIS:\s*(.+?)(?=\n\s*FILE:)", answer, re.S)
    return (diagnosis.group(1).strip() if diagnosis else ""), file_match.group(1), code_match.group(1).rstrip() + "\n"


def check_patch(file_name: str, code: str) -> list:
    """SAFETY GATE: reasons to refuse the LLM's code. An empty list means it may be applied."""
    if file_name not in EDITABLE_FILES:
        return [f"'{file_name}' is not a file the repair agent may change."]
    if len(code) > 20000:
        return ["The file is suspiciously large."]
    try:
        tree = ast.parse(code)
    except SyntaxError as err:
        return [f"The proposed code does not parse: {err.msg} (line {err.lineno})."]
    allowed = ALLOWED_IMPORTS | ({"os"} if file_name == "database.py" else set())
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [(node.module or "").split(".")[0]]
        else:
            modules = []
        problems += [f"Import of '{m}' is not allowed." for m in modules if m not in allowed]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
            problems.append(f"Call to '{node.func.id}()' is not allowed.")
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "os"
                and node.attr not in ("getenv", "environ")):
            problems.append(f"'os.{node.attr}' is not allowed.")
    return problems


def repair_project(folder: str, spec: dict, llm=generate, runner=run_tests) -> dict:
    project_dir = GENERATED_DIR / folder
    backups = project_dir / ".repair_backups"
    tests = runner(folder)
    if tests["success"]:
        return {"needed": False, "fixed": True, "attempts": [], "final_tests": tests}

    attempts, history = [], []
    for number in range(1, MAX_ATTEMPTS + 1):
        analysis = analyze_failure(tests)
        record = {"attempt": number, "error_type": analysis["error_type"], "error_message": analysis["summary"][:1000],
                  "file": "", "diagnosis": "", "result": "", "passed_before": tests["passed"],
                  "passed_after": tests["passed"], "total": tests["total"]}
        attempts.append(record)
        try:
            answer = llm(SYSTEM, build_prompt(project_dir, spec, tests, analysis, history))
        except LLMError as err:
            record["result"], record["diagnosis"] = "llm_unavailable", str(err)
            break
        parsed = parse_answer(answer)
        if parsed is None:
            record["result"] = "unreadable_answer"
            history.append("Your previous answer did not follow the required format.")
            continue
        record["diagnosis"], record["file"], code = parsed
        problems = check_patch(record["file"], code)
        if problems:
            record["result"] = "rejected_by_safety_check"
            record["diagnosis"] += " | REJECTED: " + " ".join(problems)
            history.append(f"A change to {record['file']} was rejected: {' '.join(problems)}")
            continue

        target = project_dir / record["file"]
        original = target.read_text(encoding="utf-8")
        backups.mkdir(exist_ok=True)
        (backups / f"attempt_{number}_{record['file']}").write_text(original, encoding="utf-8")
        target.write_text(code, encoding="utf-8")

        new_tests = runner(folder)
        record["passed_after"], record["total"] = new_tests["passed"], new_tests["total"]
        if new_tests["success"]:
            record["result"], tests = "fixed", new_tests
            break
        if new_tests["passed"] > tests["passed"]:
            record["result"], tests = "improved", new_tests           # keep it and continue from here
            history.append(f"Changing {record['file']} helped but tests still fail: {record['diagnosis']}")
        else:
            target.write_text(original, encoding="utf-8")             # undo: it did not help
            record["result"] = "no_improvement_reverted"
            history.append(f"Changing {record['file']} did not help and was undone: {record['diagnosis']}")

    if not tests["success"] and attempts and attempts[-1]["result"] == "no_improvement_reverted":
        tests = runner(folder)        # make the stored results describe the code that is really on disk
    return {"needed": True, "fixed": tests["success"], "attempts": attempts, "final_tests": tests}