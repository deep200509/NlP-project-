"""
Conversation memory: everything is stored in the database, nothing inside the AI model.

  user / assistant messages -> what was said (shown in the chat and in the history page)
  system messages           -> the agent's state (slots + stage) as JSON

To continue a conversation days later, the agent simply loads the latest system message.
"""
import json

from sqlalchemy.orm import Session

from app.agent.planner import handle_message, new_state, result_reply
from app.code_generator.project_generator import generate_project
from app.database.models import Conversation, Message, Project, User, utc_now
from app.projects.routes import _save_test_result, _summary
from app.testing.runner import run_tests


def load_state(conversation: Conversation) -> dict:
    for message in reversed(conversation.messages):
        if message.role == "system":
            return json.loads(message.content)
    return new_state()


def _add(db: Session, conversation: Conversation, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation.id, role=role, content=content)
    db.add(message)
    return message


def _build(db: Session, user: User, conversation: Conversation, spec: dict) -> tuple[Project, dict]:
    """GENERATE + TEST, and save the project linked to this conversation."""
    folder = f"u{user.id}_{spec['slug']}"
    generated = generate_project(spec, folder=folder)
    project = db.query(Project).filter(Project.user_id == user.id,
                                       Project.generated_code_path == generated["project_dir"]).first()
    if project is None:
        project = Project(user_id=user.id, generated_code_path=generated["project_dir"])
        db.add(project)
    project.conversation_id = conversation.id
    project.project_name = spec["project_name"]
    project.requirement = " ".join(m.content for m in conversation.messages if m.role == "user")
    project.api_specification = json.dumps(spec)
    project.status = "generated"
    db.commit()
    db.refresh(project)

    tests = run_tests(folder)
    _save_test_result(project, tests, db)
    if not tests["success"]:                       # REPAIR stage: only runs when something failed
        from app.agent.repair import repair_project
        from app.agent.repair_routes import save_repair
        outcome = repair_project(folder, spec)
        save_repair(project, outcome, db)
        tests = outcome["final_tests"]
    # DOCUMENT stage: README.md, API.md and openapi.json
    from app.code_generator.project_generator import GENERATED_DIR
    from app.documentation.generator import write_documentation
    write_documentation(GENERATED_DIR / folder, spec, project.requirement)
    return project, tests


def process_message(db: Session, user: User, conversation: Conversation, text: str) -> dict:
    """One full turn: store the user's message, let the agent think, store the reply and the new state."""
    state = load_state(conversation)
    _add(db, conversation, "user", text)
    db.commit()
    db.refresh(conversation)

    turn = handle_message(state, text)
    state, reply, project = turn["state"], turn["reply"], None

    if turn["action"] == "generate":
        project, tests = _build(db, user, conversation, turn["spec"])
        state["stage"], state["project_id"] = "DONE", project.id
        reply = result_reply(project.project_name, tests, project.id)

    if conversation.title == "New conversation" and state["resource"]:
        conversation.title = f"{state['resource'].title()} Management API"
    _add(db, conversation, "assistant", reply)
    _add(db, conversation, "system", json.dumps(state))
    conversation.updated_at = utc_now()          # so the history page shows the most recent chat first
    db.commit()
    db.refresh(conversation)

    return {"reply": reply, "stage": state["stage"], "waiting_for": state["pending"],
            "specification": turn["spec"], "project": _summary(project) if project else None,
            "conversation": {"id": conversation.id, "title": conversation.title}}