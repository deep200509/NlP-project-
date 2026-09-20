"""All database tables of the application (section 8 and 9 of the project plan)."""
import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))     # never the password itself
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utc_now)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan",
                                                     order_by="Message.id")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))               # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime, default=utc_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    project_name: Mapped[str] = mapped_column(String(200))
    requirement: Mapped[str] = mapped_column(Text)
    api_specification: Mapped[str] = mapped_column(Text)        # the specification as JSON text
    generated_code_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="generated")   # generated | tests_passed | tests_failed
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship(back_populates="projects")
    test_results: Mapped[list["TestResult"]] = relationship(back_populates="project", cascade="all, delete-orphan",
                                                            order_by="TestResult.id")


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    passed: Mapped[int] = mapped_column(Integer)
    failed: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean)
    report: Mapped[str] = mapped_column(Text)                   # the readable PASS / FAIL report
    results_json: Mapped[str] = mapped_column(Text)             # every test with its details
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="test_results")