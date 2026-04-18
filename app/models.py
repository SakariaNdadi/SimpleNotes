from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    notes: Mapped[list[Note]] = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    labels: Mapped[list[Label]] = relationship("Label", back_populates="user", cascade="all, delete-orphan")
    llm_configs: Mapped[list[UserLLMConfig]] = relationship("UserLLMConfig", back_populates="user", cascade="all, delete-orphan")
    calendar_tokens: Mapped[list[CalendarToken]] = relationship("CalendarToken", back_populates="user", cascade="all, delete-orphan")
    reset_tokens: Mapped[list[PasswordResetToken]] = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    verify_tokens: Mapped[list[EmailVerificationToken]] = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped[UserPreferences | None] = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship("User", back_populates="reset_tokens")


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship("User", back_populates="verify_tokens")


class Label(Base):
    __tablename__ = "labels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")

    user: Mapped[User] = relationship("User", back_populates="labels")
    notes: Mapped[list[Note]] = relationship("Note", back_populates="label")

    __table_args__ = (UniqueConstraint("user_id", "title", name="uq_label_user_title"),)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    label_id: Mapped[str | None] = mapped_column(ForeignKey("labels.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="notes")
    label: Mapped[Label | None] = relationship("Label", back_populates="notes")
    tasks: Mapped[list[NoteTask]] = relationship("NoteTask", back_populates="note", cascade="all, delete-orphan")
    summaries: Mapped[list[NoteSummary]] = relationship("NoteSummary", back_populates="note", cascade="all, delete-orphan")
    history: Mapped[list[NoteHistory]] = relationship("NoteHistory", back_populates="note", cascade="all, delete-orphan")


class UserLLMConfig(Base):
    __tablename__ = "user_llm_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship("User", back_populates="llm_configs")


class CalendarToken(Base):
    __tablename__ = "calendar_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # google | microsoft
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="calendar_tokens")

    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_calendar_user_provider"),)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    font: Mapped[str] = mapped_column(String(50), default="inter")
    palette: Mapped[str] = mapped_column(String(50), default="default")
    save_ai_summaries: Mapped[bool] = mapped_column(Boolean, default=False)
    max_edit_history: Mapped[int] = mapped_column(Integer, default=3)
    languages: Mapped[str] = mapped_column(Text, default='["en"]')

    user: Mapped[User] = relationship("User", back_populates="preferences")


class NoteTask(Base):
    __tablename__ = "note_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    task_type: Mapped[str] = mapped_column(String(20), default="task")
    due_datetime: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="local", nullable=False)
    source: Mapped[str] = mapped_column(String(10), default="llm", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    note: Mapped[Note] = relationship("Note", back_populates="tasks")


class NoteSummary(Base):
    __tablename__ = "note_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    note: Mapped[Note] = relationship("Note", back_populates="summaries")


class NoteHistory(Base):
    __tablename__ = "note_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    label_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    note: Mapped[Note] = relationship("Note", back_populates="history")
