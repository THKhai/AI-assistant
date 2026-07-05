import json
from datetime import datetime

from sqlmodel import Session, select

from src.core.db import get_engine, _to_dict
from src.core.models import KnowledgeDoc


class KnowledgeService:
    """Knowledge document index management."""

    def upsert(self, module: str, doc_id: str, filepath: str, title: str, tags: list[str]):
        with Session(get_engine()) as s:
            row = s.exec(select(KnowledgeDoc).where(KnowledgeDoc.doc_id == doc_id)).first()
            now = datetime.utcnow()
            if row:
                row.indexed_at = now
                row.updated_at = now
                row.deleted = 0
            else:
                row = KnowledgeDoc(
                    module=module, doc_id=doc_id, filepath=filepath,
                    title=title, tags=json.dumps(tags), indexed_at=now,
                )
            s.add(row)
            s.commit()

    def is_indexed(self, doc_id: str) -> bool:
        with Session(get_engine()) as s:
            row = s.exec(
                select(KnowledgeDoc)
                .where(KnowledgeDoc.doc_id == doc_id, KnowledgeDoc.deleted == 0)
            ).first()
        return row is not None
