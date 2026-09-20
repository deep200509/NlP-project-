"""
Project generator: API specification -> a complete FastAPI project on disk.

    generated_projects/<slug>/
        main.py  database.py  models.py  schemas.py  crud.py
        requirements.txt  README.md  spec.json
        tests/test_api.py  tests/labels.json
"""
import json

from app.code_generator.crud_generator import generate_crud
from app.code_generator.model_generator import generate_models
from app.code_generator.route_generator import generate_main
from app.code_generator.schema_generator import generate_schemas
from app.config import PROJECT_DIR
from app.testing.test_generator import generate_test_files

GENERATED_DIR = PROJECT_DIR / "generated_projects"

REQUIREMENTS = "fastapi>=0.110\nuvicorn[standard]>=0.29\nsqlalchemy>=2.0\npytest>=8.0\nhttpx>=0.27\n"


def generate_database(spec: dict) -> str:
    return f'''"""Database connection. Generated automatically from the API specification."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite by default. For PostgreSQL set the DATABASE_URL environment variable, e.g.
# postgresql+psycopg://user:password@localhost:5432/{spec["slug"]}
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./{spec["slug"]}.db")

connect_args = {{"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {{}}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''


def generate_readme(spec: dict) -> str:
    lines = [f"# {spec['project_name']}", "",
             "Generated automatically from a natural-language requirement.", "",
             "## Run", "", "```", "pip install -r requirements.txt", "uvicorn main:app --reload --port 8001", "```", "",
             "Interactive documentation: http://127.0.0.1:8001/docs", "",
             "## Endpoints", "", "| Method | Path | Description |", "|---|---|---|"]
    lines += [f"| {e['method']} | `{e['path']}` | {e['summary']} |" for e in spec["endpoints"]]
    lines += ["", f"## Table `{spec['table_name']}`", "", "| Field | Type | Required | Unique |", "|---|---|---|---|",
              "| id | integer | auto | yes |"]
    lines += [f"| {f['name']} | {f['type']} | {'yes' if f.get('required', True) else 'no'} | "
              f"{'yes' if f.get('unique') else 'no'} |" for f in spec["fields"]]
    if spec.get("auth_required"):
        lines += ["", "> Authentication was requested in the requirement. It is not part of this generated version yet."]
    return "\n".join(lines) + "\n"


def generate_project(spec: dict) -> dict:
    files = {
        "database.py": generate_database(spec),
        "models.py": generate_models(spec),
        "schemas.py": generate_schemas(spec),
        "crud.py": generate_crud(spec),
        "main.py": generate_main(spec),
        "requirements.txt": REQUIREMENTS,
        "README.md": generate_readme(spec),
        "spec.json": json.dumps(spec, indent=2),
        **generate_test_files(spec),   # tests/test_api.py + tests/labels.json
    }

    # safety net: never write Python that does not even parse
    for name, source in files.items():
        if name.endswith(".py"):
            compile(source, name, "exec")

    project_dir = GENERATED_DIR / spec["slug"]
    project_dir.mkdir(parents=True, exist_ok=True)
    old_database = project_dir / f"{spec['slug']}.db"
    if old_database.exists():          # the table layout may have changed
        try:
            old_database.unlink()
        except PermissionError:        # Windows: the generated API is still running and holds the file
            pass
    for name, source in files.items():
        path = project_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)   # creates tests/ when needed
        path.write_text(source, encoding="utf-8")

    return {
        "project_dir": str(project_dir),
        "files": [{"name": n, "lines": s.count("\n")} for n, s in files.items()],
        "run": [f"cd {project_dir}", "uvicorn main:app --reload --port 8001"],
        "docs_url": "http://127.0.0.1:8001/docs",
    }