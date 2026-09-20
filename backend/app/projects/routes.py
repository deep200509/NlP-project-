"""
Projects: every generated API belongs to the user who created it.
Every route needs a login, and every query filters by user_id, so one user can never see another's work.
"""
import json
import shutil

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.code_generator.project_generator import GENERATED_DIR, generate_project
from app.database.database import get_db
from app.database.models import Project, TestResult, User
from app.nlp.requirement_analyzer import analyze_requirement
from app.specification.generator import build_spec
from app.specification.routes import QUESTIONS, check
from app.testing.runner import run_tests

router = APIRouter(prefix="/projects", tags=["Projects"])


class RequirementIn(BaseModel):
    text: str = Field(min_length=2, max_length=3000, examples=[
        "Create an API for a student management system. A student should have name, "
        "email, age and course. Users should be able to add students, view all students, "
        "find a student by ID, update student details and delete students."])


def _folder(project: Project) -> str:
    return project.generated_code_path.replace("\\", "/").rstrip("/").split("/")[-1]


def _own_project(project_id: int, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if project is None:        # also the answer when the project belongs to someone else
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _save_test_result(project: Project, tests: dict, db: Session) -> None:
    db.add(TestResult(project_id=project.id, passed=tests["passed"], failed=tests["failed"],
                      total=tests["total"], success=tests["success"], report=tests["report"],
                      results_json=json.dumps(tests["results"])))
    project.status = "tests_passed" if tests["success"] else "tests_failed"
    db.commit()
    db.refresh(project)


def _summary(project: Project) -> dict:
    spec = json.loads(project.api_specification)
    latest = project.test_results[-1] if project.test_results else None
    return {"id": project.id, "project_name": project.project_name, "status": project.status,
            "endpoints": len(spec["endpoints"]),
            "tests": f"{latest.passed}/{latest.total} tests passed" if latest else "not tested",
            "created_at": project.created_at, "updated_at": project.updated_at}


@router.post("", status_code=201)
def create_project(body: RequirementIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Requirement text -> generated, tested API that is saved to the logged-in user's account."""
    analysis = analyze_requirement(body.text)
    if not analysis["complete"]:
        resource = analysis["resource"] or "item"
        raise HTTPException(status_code=422, detail={
            "message": "The requirement is incomplete.", "missing": analysis["missing"],
            "questions": [QUESTIONS[m].format(resource=resource) for m in analysis["missing"]]})
    spec = build_spec(analysis)
    validation = check(spec)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail={"message": "The specification is not valid.",
                                                     "errors": validation["errors"]})

    folder = f"u{user.id}_{spec['slug']}"           # each user gets separate folders
    generated = generate_project(spec, folder=folder)

    project = db.query(Project).filter(Project.user_id == user.id,
                                       Project.generated_code_path == generated["project_dir"]).first()
    if project is None:                              # generating the same API again updates the old row
        project = Project(user_id=user.id, generated_code_path=generated["project_dir"])
        db.add(project)
    project.project_name = spec["project_name"]
    project.requirement = body.text
    project.api_specification = json.dumps(spec)
    project.status = "generated"
    db.commit()
    db.refresh(project)

    tests = run_tests(folder)
    _save_test_result(project, tests, db)
    return {**_summary(project), "warnings": validation["warnings"], "report": tests["report"].split("\n")}


@router.get("")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.user_id == user.id).order_by(Project.id.desc()).all()
    return [_summary(p) for p in projects]


@router.get("/{project_id}")
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _own_project(project_id, user, db)
    folder = GENERATED_DIR / _folder(project)
    files = sorted(str(p.relative_to(folder)).replace("\\", "/") for p in folder.rglob("*")
                   if p.is_file() and p.suffix in (".py", ".md", ".txt", ".json") and "__pycache__" not in p.parts)
    latest = project.test_results[-1] if project.test_results else None
    return {**_summary(project), "requirement": project.requirement,
            "specification": json.loads(project.api_specification), "files": files,
            "test_report": latest.report.split("\n") if latest else [],
            "test_runs": len(project.test_results)}


@router.post("/{project_id}/run-tests")
def rerun_tests(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _own_project(project_id, user, db)
    tests = run_tests(_folder(project))
    _save_test_result(project, tests, db)
    return {**_summary(project), "report": tests["report"].split("\n")}


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _own_project(project_id, user, db)
    folder = GENERATED_DIR / _folder(project)
    if folder.is_dir() and folder.parent == GENERATED_DIR:      # never delete anything outside generated_projects
        shutil.rmtree(folder, ignore_errors=True)
    db.delete(project)
    db.commit()