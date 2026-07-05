import json
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, select

from src.core import config
from src.core.db import get_engine, _to_dict
from src.core.models import Conversation, Plan, Task


class PlanService:
    """Plan and task persistence."""

    def save(self, module: str, level: str, period: str, content: dict) -> int:
        with Session(get_engine()) as s:
            row = Plan(module=module, level=level, period=period, content=json.dumps(content))
            s.add(row)
            s.commit()
            s.refresh(row)
            return row.id

    def get(self, module: str, level: str, period: str) -> dict | None:
        with Session(get_engine()) as s:
            row = s.exec(
                select(Plan)
                .where(Plan.module == module, Plan.level == level,
                       Plan.period == period, Plan.deleted == 0)
                .order_by(Plan.id.desc())
                .limit(1)
            ).first()
        if not row:
            return None
        d = _to_dict(row)
        d["content"] = json.loads(d["content"])
        return d

    def save_tasks(self, plan_id: int, module: str, tasks: list[str], due_date: str = None):
        with Session(get_engine()) as s:
            for t in tasks:
                s.add(Task(plan_id=plan_id, module=module, description=t, due_date=due_date))
            s.commit()

    def get_tasks(self, plan_id: int) -> list[dict]:
        with Session(get_engine()) as s:
            rows = s.exec(
                select(Task).where(Task.plan_id == plan_id, Task.deleted == 0).order_by(Task.id)
            ).all()
        return [_to_dict(r) for r in rows]

    def update_task_status(self, task_id: int, status: str):
        with Session(get_engine()) as s:
            row = s.get(Task, task_id)
            if row:
                row.status = status
                row.updated_at = datetime.utcnow()
                s.add(row)
                s.commit()


class ConversationService:
    """Conversation turn storage and retrieval."""

    def next_turn(self, session_id: str) -> int:
        with Session(get_engine()) as s:
            result = s.scalar(
                select(func.coalesce(func.max(Conversation.turn), 0))
                .where(Conversation.session_id == session_id)
            )
        return (result or 0) + 1

    def save_turn(self, session_id: str, module: str, session_type: str,
                  turn: int, role: str, content: str):
        with Session(get_engine()) as s:
            s.add(Conversation(
                module=module, session_type=session_type, session_id=session_id,
                turn=turn, role=role, content=content,
            ))
            s.commit()

    def get_recent(self, session_id: str, limit: int = None) -> list[dict]:
        limit = limit or config.CONVERSATION_HISTORY_TURNS * 2
        with Session(get_engine()) as s:
            rows = s.exec(
                select(Conversation)
                .where(Conversation.session_id == session_id, Conversation.deleted == 0)
                .order_by(Conversation.turn)
                .limit(limit)
            ).all()
        return [{"role": r.role, "content": r.content} for r in rows]
