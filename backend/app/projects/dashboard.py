"""The numbers and lists shown on the dashboard page (section 6 of the project plan)."""
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database.database import get_db
from app.database.models import Conversation, Project, RepairAttempt, User
from app.projects.routes import _summary

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.user_id == user.id).order_by(Project.id.desc()).all()
    conversations = (db.query(Conversation).filter(Conversation.user_id == user.id)
                     .order_by(Conversation.updated_at.desc()).all())
    repairs_fixed = (db.query(RepairAttempt).join(Project)
                     .filter(Project.user_id == user.id, RepairAttempt.result == "fixed").count())

    last = conversations[0] if conversations else None
    visible = [m for m in last.messages if m.role != "system"] if last else []
    return {
        "total_projects": len(projects),
        "total_endpoints": sum(len(json.loads(p.api_specification)["endpoints"]) for p in projects),
        "projects_passing": sum(p.status == "tests_passed" for p in projects),
        "repairs_fixed": repairs_fixed,
        "total_conversations": len(conversations),
        "recent_projects": [_summary(p) for p in projects[:5]],
        "last_conversation": {"id": last.id, "title": last.title,
                              "last_message": visible[-1].content.split("\n")[0][:120] if visible else ""} if last else None,
    }