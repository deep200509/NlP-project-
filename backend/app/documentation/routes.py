"""Documentation and download endpoints for a project."""
import io
import json
import zipfile

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.code_generator.project_generator import GENERATED_DIR
from app.database.database import get_db
from app.database.models import User
from app.documentation.generator import write_documentation
from app.projects.routes import _folder, _own_project

router = APIRouter(prefix="/projects", tags=["Documentation"])

SKIP_FOLDERS = {"__pycache__", ".repair_backups", ".pytest_cache", "venv"}
SKIP_FILES = {"junit.xml"}


def make_zip(project_dir, top_folder: str) -> bytes:
    """The project as a zip file, without databases, caches and repair backups."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(project_dir.rglob("*")):
            relative = path.relative_to(project_dir)
            if (not path.is_file() or path.suffix == ".db" or path.name in SKIP_FILES
                    or SKIP_FOLDERS & set(relative.parts)):
                continue
            archive.write(path, f"{top_folder}/{relative.as_posix()}")
    return buffer.getvalue()


@router.post("/{project_id}/documentation")
def create_documentation(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Writes README.md, API.md and openapi.json into the project folder."""
    project = _own_project(project_id, user, db)
    spec = json.loads(project.api_specification)
    return write_documentation(GENERATED_DIR / _folder(project), spec, project.requirement)


@router.get("/{project_id}/download")
def download_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The whole project as a zip file, with fresh documentation inside."""
    project = _own_project(project_id, user, db)
    spec = json.loads(project.api_specification)
    project_dir = GENERATED_DIR / _folder(project)
    write_documentation(project_dir, spec, project.requirement)
    return Response(content=make_zip(project_dir, spec["slug"]), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{spec["slug"]}.zip"'})