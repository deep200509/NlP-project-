"""Endpoints for the self-repair loop (and for breaking a project on purpose, to demonstrate it)."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.faults import catalogue, inject
from app.agent.repair import MAX_ATTEMPTS, repair_project
from app.auth.security import get_current_user
from app.code_generator.project_generator import GENERATED_DIR
from app.database.database import get_db
from app.database.models import Project, RepairAttempt, User
from app.llm.client import LLMError, describe, generate
from app.projects.routes import _folder, _own_project, _save_test_result, _summary
from app.testing.runner import run_tests

router = APIRouter(tags=["Self-repair"], dependencies=[Depends(get_current_user)])


def save_repair(project: Project, outcome: dict, db: Session) -> dict:
    """Stores every attempt and the final test result; returns a readable summary."""
    for a in outcome["attempts"]:
        db.add(RepairAttempt(project_id=project.id, **a))
    _save_test_result(project, outcome["final_tests"], db)
    return {**_summary(project), "repair_needed": outcome["needed"], "fixed": outcome["fixed"],
            "attempts_used": f"{len(outcome['attempts'])}/{MAX_ATTEMPTS}", "attempts": outcome["attempts"],
            "report": outcome["final_tests"]["report"].split("\n")}


@router.get("/llm/status")
def llm_status():
    """Checks that the language model is reachable. Costs one tiny request."""
    info = describe()
    try:
        answer = generate("You are a connection test.", "Reply with exactly one word: ready")
        return {**info, "reachable": True, "answer": answer.strip()[:50]}
    except LLMError as err:
        return {**info, "reachable": False, "problem": str(err)}


@router.get("/projects/{project_id}/bugs")
def available_bugs(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _own_project(project_id, user, db)
    spec = json.loads(project.api_specification)
    return {name: f"{fault['description']} ({fault['file']})" for name, fault in catalogue(spec).items()}


@router.post("/projects/{project_id}/inject-bug/{bug}")
def inject_bug(project_id: int, bug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Breaks the generated code in a known way, then runs the tests so you can see them fail."""
    project = _own_project(project_id, user, db)
    try:
        injected = inject(GENERATED_DIR / _folder(project), json.loads(project.api_specification), bug)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    tests = run_tests(_folder(project))
    _save_test_result(project, tests, db)
    return {**_summary(project), "injected": injected, "report": tests["report"].split("\n")}


@router.post("/projects/{project_id}/repair")
def repair(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Runs the repair loop: analyse -> fix -> retest, at most 3 attempts. Every attempt is stored."""
    project = _own_project(project_id, user, db)
    outcome = repair_project(_folder(project), json.loads(project.api_specification))
    return save_repair(project, outcome, db)


@router.get("/projects/{project_id}/repairs")
def repair_history(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _own_project(project_id, user, db)
    return [{"attempt": a.attempt, "error_type": a.error_type, "error_message": a.error_message, "file": a.file,
             "diagnosis": a.diagnosis, "result": a.result, "tests": f"{a.passed_before} -> {a.passed_after} of {a.total}",
             "created_at": a.created_at} for a in project.repair_attempts]