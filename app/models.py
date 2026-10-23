"""Tabelas da base de dados."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class TelemetriaModel(Base):
    """Uma leitura de sensores de um poço. Nunca é alterada depois de gravada."""

    __tablename__ = "telemetria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poco_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=agora_utc)
    pressao_bar: Mapped[float] = mapped_column(Float)
    temperatura_celsius: Mapped[float] = mapped_column(Float)
    caudal_oleo_m3h: Mapped[float] = mapped_column(Float)
    abertura_choke_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    status_seguranca: Mapped[str] = mapped_column(String(16))
    anomalia_ml: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fonte: Mapped[str] = mapped_column(String(32), default="simulacao")


class ComandoModel(Base):
    """Comando enviado da consola de controlo para o campo, com auditoria completa.

    O campo (simulador) vai buscar os comandos pendentes à API: a ligação
    parte sempre do lado industrial para fora, nunca o contrário.
    """

    __tablename__ = "comandos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poco_id: Mapped[str] = mapped_column(String(64), index=True)
    acao: Mapped[str] = mapped_column(String(32))
    estado: Mapped[str] = mapped_column(String(16), default="PENDENTE")  # PENDENTE / EXECUTADO / REJEITADO
    operador: Mapped[str] = mapped_column(String(64), default="desconhecido")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora_utc)
    executado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detalhe: Mapped[str | None] = mapped_column(String(255), nullable=True)
