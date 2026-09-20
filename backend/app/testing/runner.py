"""
Test runner: runs the generated tests in a SEPARATE process and reads the results.

Safety: the generated code never runs inside our own server. It gets its own
Python process, its own database file and a time limit.
"""
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from app.code_generator.project_generator import GENERATED_DIR

TIMEOUT_SECONDS = 120
SLUG = re.compile(r"^[a-z][a-z0-9_]*$")


def _read_junit(xml_path, labels: dict) -> list:
    results = []
    for case in ET.parse(xml_path).getroot().iter("testcase"):
        name = case.get("name", "")
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        status = "SKIP" if case.find("skipped") is not None else ("FAIL" if problem is not None else "PASS")
        label = labels.get(name, {"endpoint": "(setup)", "check": name})
        results.append({
            "test": name, "endpoint": label["endpoint"], "check": label["check"], "status": status,
            "message": (problem.get("message") or "")[:300] if problem is not None else "",
            "details": (problem.text or "")[-1500:] if problem is not None else "",
        })
    return results


def _text_report(results: list, passed: int) -> str:
    width = max((len(r["endpoint"]) for r in results), default=10) + 2
    lines = ["API TEST RESULTS", ""]
    for r in results:
        mark = {"PASS": "✓ PASS", "FAIL": "✗ FAIL", "SKIP": "- SKIP"}[r["status"]]
        lines.append(f"{r['endpoint']:<{width}}{mark}   {r['check']}")
    lines += ["", f"{passed}/{len(results)} Tests Passed"]
    return "\n".join(lines)


def run_tests(slug: str) -> dict:
    if not SLUG.match(slug):
        raise ValueError("Invalid project name.")
    project_dir = GENERATED_DIR / slug
    if not (project_dir / "tests" / "test_api.py").exists():
        raise FileNotFoundError(f"No generated tests found for '{slug}'. Generate the project first.")

    xml_path = project_dir / "tests" / "junit.xml"
    for leftover in (xml_path, project_dir / "test_run.db"):
        if leftover.exists():
            leftover.unlink()

    started = time.time()
    try:
        process = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", f"--junitxml={xml_path}"],
            cwd=project_dir, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=TIMEOUT_SECONDS)
        output = (process.stdout or "") + (process.stderr or "")
    except subprocess.TimeoutExpired:
        output, process = f"Tests did not finish within {TIMEOUT_SECONDS} seconds.", None

    labels = json.loads((project_dir / "tests" / "labels.json").read_text(encoding="utf-8"))
    results = _read_junit(xml_path, labels) if xml_path.exists() else []
    passed = sum(r["status"] == "PASS" for r in results)
    failed = sum(r["status"] == "FAIL" for r in results)

    summary = {
        "project": slug,
        "success": bool(results) and failed == 0,
        "passed": passed, "failed": failed, "total": len(results),
        "duration_seconds": round(time.time() - started, 1),
        "report": _text_report(results, passed),
        "results": results,
        # when something goes wrong, the repair agent (later phase) reads this
        "log_tail": "" if results and failed == 0 else output[-3000:],
    }
    (project_dir / "test_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary