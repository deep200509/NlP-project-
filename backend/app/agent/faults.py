"""
Fault injection: deliberately breaks a generated project in a known way.

Our templates produce correct code, so the repair agent would never have anything to do.
Injecting known bugs lets us DEMONSTRATE the repair loop and MEASURE its success rate
(this is how the evaluation in the final phase works).
"""


def catalogue(spec: dict) -> dict:
    resource = spec["resource"]
    return {
        "wrong_status_code": {
            "description": "POST returns 200 instead of 201", "file": "main.py",
            "find": "status_code=201", "replace": "status_code=200"},
        "wrong_error_code": {
            "description": "an unknown id gives 400 instead of 404", "file": "main.py",
            "find": "raise HTTPException(status_code=404", "replace": "raise HTTPException(status_code=400"},
        "delete_does_nothing": {
            "description": "the delete function forgets to delete", "file": "crud.py",
            "find": "    db.delete(item)\n", "replace": ""},
        "update_ignores_data": {
            "description": "the update function ignores the new values", "file": "crud.py",
            "find": "        setattr(item, key, value)\n", "replace": "        pass\n"},
        "name_error": {
            "description": "a misspelled variable name crashes the create function", "file": "crud.py",
            "find": "    db.refresh(item)\n    return item\n", "replace": "    db.refresh(item)\n    return itm\n"},
        "syntax_error": {
            "description": "a missing colon makes crud.py impossible to import", "file": "crud.py",
            "find": f"def get_{resource}(db: Session, {resource}_id: int):",
            "replace": f"def get_{resource}(db: Session, {resource}_id: int)"},
    }


def inject(project_dir, spec: dict, bug: str) -> dict:
    faults = catalogue(spec)
    if bug not in faults:
        raise ValueError(f"Unknown bug '{bug}'. Choose one of: {', '.join(faults)}")
    fault = faults[bug]
    path = project_dir / fault["file"]
    source = path.read_text(encoding="utf-8")
    if fault["find"] not in source:
        raise ValueError(f"Bug '{bug}' does not apply to this project (the code it changes is not there).")
    path.write_text(source.replace(fault["find"], fault["replace"], 1), encoding="utf-8")
    return {"bug": bug, "file": fault["file"], "description": fault["description"]}