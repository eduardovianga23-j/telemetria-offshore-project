"""Esquemas Pydantic: o contrato de dados entre campo, API e dashboards."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _utc(valor: datetime | None) -> datetime | None:
    # O SQLite devolve datas sem fuso: todas as datas do sistema estão em UTC
    if valor is not None and valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


DataUTC = Annotated[datetime, AfterValidator(_utc)]

AcaoComando = Literal["ALIVIAR_PRESSAO", "REPOR_NORMAL"]


class TelemetriaIn(BaseModel):
    """Leitura enviada pelo campo. A API decide o estado de segurança, não o emissor."""

    poco_id: str = Field(..., min_length=1, max_length=64, examples=["B17-A"])
    pressao_bar: float = Field(..., ge=0, le=1000, examples=[128.4])
    temperatura_celsius: float = Field(..., ge=-50, le=300, examples=[78.2])
    caudal_oleo_m3h: float = Field(..., ge=0, le=10_000, examples=[95.0])
    abertura_choke_pct: float | None = Field(default=None, ge=0, le=100, examples=[45.0])
    timestamp: datetime | None = Field(default=None, description="UTC; se faltar, usa a hora da API")
    fonte: str = Field(default="simulacao", max_length=32, examples=["simulacao", "volve"])


class TelemetriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    poco_id: str
    timestamp: DataUTC
    pressao_bar: float
    temperatura_celsius: float
    caudal_oleo_m3h: float
    abertura_choke_pct: float | None
    status_seguranca: str
    anomalia_ml: bool | None
    fonte: str


class ComandoIn(BaseModel):
    poco_id: str = Field(..., min_length=1, max_length=64, examples=["B17-A"])
    acao: AcaoComando = Field(..., examples=["ALIVIAR_PRESSAO"])
    operador: str = Field(default="operador-sala-controlo", max_length=64)


class ComandoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    poco_id: str
    acao: str
    estado: str
    operador: str
    criado_em: DataUTC
    executado_em: DataUTC | None
    detalhe: str | None


class ComandoConfirmacao(BaseModel):
    estado: Literal["EXECUTADO", "REJEITADO"]
    detalhe: str | None = Field(default=None, max_length=255)


class ResumoPoco(BaseModel):
    poco_id: str
    ultima_leitura: DataUTC
    pressao_bar: float
    status_seguranca: str
    fonte: str


class InfoSistema(BaseModel):
    modo_dados: str
    limite_atencao_bar: float
    limite_critico_bar: float
    preco_barril_usd: float
    modelo_ml_treinado: bool
