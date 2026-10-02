"""Small transactional persistence boundary for the local demo.

SQLite is the default developer store; the URL can point at a SQLAlchemy-supported
database later. Results are immutable JSON snapshots so the simulator remains pure.
"""

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DATABASE_URL = os.getenv("MAYA_DATABASE_URL", "sqlite:///./maya.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


class Base(DeclarativeBase):
    pass


class Snapshot(Base):
    __tablename__ = "maya_snapshots"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SyncReceipt(Base):
    __tablename__ = "maya_sync_receipts"
    event_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))
    record_id: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def init_db() -> None:
    Path(".").mkdir(parents=True, exist_ok=True)
    # Tests and local resets may remove the SQLite file between app lifecycles.
    # Drop pooled handles so SQLAlchemy cannot keep writing to the unlinked
    # inode or retain snapshots from the previous local store.
    if DATABASE_URL.startswith("sqlite"):
        engine.dispose()
    Base.metadata.create_all(engine)


def now() -> str:
    return datetime.now(UTC).isoformat()


def put(kind: str, identifier: str, payload: dict[str, Any]) -> dict[str, Any]:
    with Session(engine) as session:
        existing = session.get(Snapshot, identifier)
        if existing is not None and existing.kind != kind:
            raise ValueError(f"ID already belongs to {existing.kind}")
        if existing is None:
            existing = Snapshot(
                id=identifier, kind=kind, payload=payload, created_at=datetime.now(UTC)
            )
            session.add(existing)
        else:
            existing.payload = payload
        session.commit()
        return payload


def get(kind: str, identifier: str) -> dict[str, Any] | None:
    with Session(engine) as session:
        row = session.scalar(
            select(Snapshot).where(Snapshot.id == identifier, Snapshot.kind == kind)
        )
        return row.payload if row else None


def all_of(kind: str) -> list[dict[str, Any]]:
    with Session(engine) as session:
        rows = session.scalars(select(Snapshot).where(Snapshot.kind == kind)).all()
        return [row.payload for row in rows]


def has_receipt(event_id: str) -> SyncReceipt | None:
    with Session(engine) as session:
        return session.get(SyncReceipt, event_id)


def add_receipt(event_id: str, payload_hash: str, status: str, record_id: str) -> None:
    with Session(engine) as session:
        if session.get(SyncReceipt, event_id) is None:
            session.add(
                SyncReceipt(
                    event_id=event_id,
                    payload_hash=payload_hash,
                    status=status,
                    record_id=record_id,
                    created_at=datetime.now(UTC),
                )
            )
            session.commit()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"
