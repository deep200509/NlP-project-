"""Extra project endpoints used by the project page: view a file, find the chat, regenerate the code."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.repair import repair_project
from app.agent.repair_routes import save_repair
from app.auth.security import get_current_user
from app.code_generator.project_generator import GENERATED_DIR, generate_project
from app.database.database import get_db
from app.database.models import User
from app.projects.routes import _folder, _own_project, _save_test_result, _summary
from app.testing.runner import run_tests

router = APIRouter(prefix="/projects", tags=["Projects"])

READABLE = (".py", ".md", ".txt", ".json")


@router.get("/{project_id}/conversation")
def project_conversation(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Which chat created this project (null when it was created without a chat)."""
    return {"conversation_id": _own_project(project_id, user, db).conversation_id}


@router.get("/{project_id}/files/{file_path:path}")
def read_file(project_id: int, file_path: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The content of one generated file, for the code viewer."""
    project = _own_project(project_id, user, db)
    folder = (GENERATED_DIR / _folder(project)).resolve()
    target = (folder / file_path).resolve()
    # never serve anything outside this project's own folder (blocks tricks like ../../.env)
    if folder not in target.parents or target.suffix not in READABLE or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return {"name": file_path, "content": target.read_text(encoding="utf-8", errors="replace")}


@router.post("/{project_id}/regenerate")
def regenerate(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Writes the code again from the stored specification, tests it and repairs it if needed."""
    project = _own_project(project_id, user, db)
    spec = json.loads(project.api_specification)
    folder = _folder(project)
    generate_project(spec, folder=folder)
    tests = run_tests(folder)
    _save_test_result(project, tests, db)
    if not tests["success"]:
        save_repair(project, repair_project(folder, spec), db)
    latest = project.test_results[-1]
    return {**_summary(project), "report": latest.report.split("\n")}