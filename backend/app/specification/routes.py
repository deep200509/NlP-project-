"""API endpoints for the specification stage."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.nlp.requirement_analyzer import analyze_requirement
from app.specification.generator import build_spec
from app.specification.schema import ApiSpec
from app.specification.validator import validate_spec

router = APIRouter(prefix="/spec", tags=["Specification"])

QUESTIONS = {
    "resource": "What is the main thing this API manages (for example: students, books, orders)?",
    "fields": "What information should each {resource} contain?",
    "operations": "What operations should the API support (add, view, update, delete, search...)?",
}


class RequirementIn(BaseModel):
    text: str = Field(min_length=2, max_length=3000, examples=[
        "Create an API for a student management system. A student should have name, "
        "email, age and course. Users should be able to add students, view all students, "
        "find a student by ID, update student details and delete students."])


def check(spec: dict) -> dict:
    """Structural check (Pydantic) + semantic check (our validator)."""
    report = validate_spec(spec)
    try:
        ApiSpec.model_validate(spec)
    except ValidationError as err:
        for problem in err.errors():
            location = ".".join(str(part) for part in problem["loc"])
            report["errors"].append(f"Structure problem at '{location}': {problem['msg']}")
        report["valid"] = False
    return report


@router.post("/from-text")
def spec_from_text(body: RequirementIn):
    """Requirement text -> analysis -> specification -> validation report."""
    try:
        analysis = analyze_requirement(body.text)
    except FileNotFoundError as err:
        raise HTTPException(status_code=503, detail=str(err))

    if not analysis["complete"]:
        resource = analysis["resource"] or "item"
        return {"status": "incomplete", "missing": analysis["missing"],
                "questions": [QUESTIONS[m].format(resource=resource) for m in analysis["missing"]],
                "spec": None, "validation": None}

    spec = build_spec(analysis)
    return {"status": "ready", "missing": [], "questions": [], "spec": spec, "validation": check(spec)}


@router.post("/validate")
def validate(spec: dict):
    """Validates a specification that was edited by hand."""
    return check(spec)