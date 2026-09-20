"""Chat endpoints: conversations, messages, history. Every route needs a login and only shows your own data."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.conversation import load_state, process_message
from app.auth.security import get_current_user
from app.database.database import get_db
from app.database.models import Conversation, Project, User

router = APIRouter(prefix="/conversations", tags=["Chat agent"])


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=3000, examples=["I want to create a library management API."])


def _own(conversation_id: int, user: User, db: Session) -> Conversation:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id,
                                                 Conversation.user_id == user.id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


def _brief(conversation: Conversation) -> dict:
    visible = [m for m in conversation.messages if m.role != "system"]
    return {"id": conversation.id, "title": conversation.title, "messages": len(visible),
            "last_message": visible[-1].content[:80] if visible else "",
            "created_at": conversation.created_at, "updated_at": conversation.updated_at}


@router.post("", status_code=201)
def start_conversation(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return _brief(conversation)


@router.get("")
def chat_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The chat history page: newest conversation first."""
    conversations = (db.query(Conversation).filter(Conversation.user_id == user.id)
                     .order_by(Conversation.updated_at.desc()).all())
    return [_brief(c) for c in conversations]


@router.get("/{conversation_id}")
def open_conversation(conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = _own(conversation_id, user, db)
    state = load_state(conversation)
    return {**_brief(conversation), "stage": state["stage"], "waiting_for": state["pending"],
            "project_id": state.get("project_id"),
            "messages": [{"role": m.role, "content": m.content, "timestamp": m.timestamp}
                         for m in conversation.messages if m.role != "system"]}


@router.post("/{conversation_id}/messages")
def send_message(conversation_id: int, body: MessageIn,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Send one message to the agent and get its reply."""
    conversation = _own(conversation_id, user, db)
    try:
        return process_message(db, user, conversation, body.content)
    except FileNotFoundError as err:
        raise HTTPException(status_code=503, detail=str(err))


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = _own(conversation_id, user, db)
    # the generated projects stay; they just lose their link to this chat
    db.query(Project).filter(Project.conversation_id == conversation.id).update({"conversation_id": None})
    db.delete(conversation)
    db.commit()