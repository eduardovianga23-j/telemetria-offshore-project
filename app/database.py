"""Ligação à base de dados (SQLite por defeito, PostgreSQL/TimescaleDB no futuro)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def init_db(db_url: str) -> Engine:
    """Cria o motor da BD e as tabelas. Chamado no arranque da API."""
    global _engine, _SessionLocal
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    _engine = create_engine(db_url, connect_args=connect_args)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)

    from app import models  # noqa: F401  (regista as tabelas)

    Base.metadata.create_all(_engine)
    return _engine


def get_db() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por pedido."""
    if _SessionLocal is None:
        raise RuntimeError("Base de dados não inicializada: chame init_db() primeiro.")
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
