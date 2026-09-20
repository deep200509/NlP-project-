"""API endpoints for the code generation stage."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.code_generator.project_generator import generate_project
from app.nlp.requirement_analyzer import analyze_requirement
from app.specification.generator import build_spec
from app.specification.routes import check

router = APIRouter(prefix="/generate", tags=["Code generation"])


class RequirementIn(BaseModel):
    text: str = Field(min_length=2, max_length=3000, examples=[
        "Create an API for a student management system. A student should have name, "
        "email, age and course. Users should be able to add students, view all students, "
        "find a student by ID, update student details and delete students."])


def _generate(spec: dict) -> dict:
    validation = check(spec)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail={"message": "The specification is not valid.",
                                                     "errors": validation["errors"]})
    try:
        result = generate_project(spec)
    except SyntaxError as err:
        raise HTTPException(status_code=500, detail=f"Generated code has a syntax error: {err}")
    return {"status": "generated", "project_name": spec["project_name"],
            "endpoints": [f"{e['method']} {e['path']}" for e in spec["endpoints"]],
            "warnings": validation["warnings"], **result}


@router.post("/from-text")
def generate_from_text(body: RequirementIn):
    """Requirement text -> analysis -> specification -> validation -> FastAPI project on disk."""
    try:
        analysis = analyze_requirement(body.text)
    except FileNotFoundError as err:
        raise HTTPException(status_code=503, detail=str(err))
    if not analysis["complete"]:
        raise HTTPException(status_code=422, detail={"message": "The requirement is incomplete.",
                                                     "missing": analysis["missing"]})
    return _generate(build_spec(analysis))


@router.post("/from-spec")
def generate_from_spec(spec: dict):
    """Generates a project from a specification (for example one that was edited by hand)."""
    return _generate(spec)