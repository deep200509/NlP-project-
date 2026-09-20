"""API endpoints for automatic testing, plus the complete MVP pipeline."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.code_generator.routes import generate_from_text
from app.testing.runner import run_tests

router = APIRouter(tags=["Testing"])


class RequirementIn(BaseModel):
    text: str = Field(min_length=2, max_length=3000, examples=[
        "Create an API for a student management system. A student should have name, "
        "email, age and course. Users should be able to add students, view all students, "
        "find a student by ID, update student details and delete students."])


def _run(slug: str) -> dict:
    try:
        return run_tests(slug)
    except (ValueError, FileNotFoundError) as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.post("/tests/run/{slug}")
def run_project_tests(slug: str):
    """Runs the generated tests of an existing project, for example: student_management"""
    return _run(slug)


@router.post("/pipeline/from-text")
def full_pipeline(body: RequirementIn):
    """The whole MVP in one call: text -> NLP -> specification -> code -> database -> tests."""
    generated = generate_from_text(body)
    slug = generated["project_dir"].replace("\\", "/").rstrip("/").split("/")[-1]
    tests = _run(slug)
    return {"status": "tested", "project_name": generated["project_name"],
            "endpoints": generated["endpoints"], "project_dir": generated["project_dir"],
            "warnings": generated["warnings"], "tests_passed": f"{tests['passed']}/{tests['total']}",
            "success": tests["success"], "report": tests["report"].split("\n"), "tests": tests}