from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Plan(SQLModel, table=True):
    __tablename__ = "plans"

    id: Optional[int] = Field(default=None, primary_key=True)
    module: str
    level: Optional[str] = None
    period: Optional[str] = None
    content: str  # JSON
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: int = Field(default=0)


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: Optional[int] = Field(default=None, foreign_key="plans.id")
    module: str
    description: str
    status: str = Field(default="pending")
    due_date: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: int = Field(default=0)


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    module: str
    session_type: Optional[str] = None
    session_id: str
    turn: int
    role: str
    content: str
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: int = Field(default=0)


class KnowledgeDoc(SQLModel, table=True):
    __tablename__ = "knowledge_docs"

    id: Optional[int] = Field(default=None, primary_key=True)
    module: str
    doc_id: str = Field(unique=True)
    filepath: str
    title: Optional[str] = None
    tags: Optional[str] = None  # JSON
    indexed_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: int = Field(default=0)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password_hash: str
    role: str = Field(default="member")
    failed_login_count: int = Field(default=0)
    locked_until: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted: int = Field(default=0)


class RevokedToken(SQLModel, table=True):
    __tablename__ = "revoked_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    jti: str = Field(unique=True)
    expires_at: datetime
    revoked_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True)
    username: str
    expires_at: datetime
    revoked: int = Field(default=0)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class TotpSecret(SQLModel, table=True):
    __tablename__ = "totp_secrets"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    secret: str
    enabled: int = Field(default=0)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
