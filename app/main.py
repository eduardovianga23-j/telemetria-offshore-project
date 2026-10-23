"""API central do Digital Twin.

Separação de responsabilidades (como numa operação real):
- O campo (simulador ou gateway) ENVIA telemetria e VAI BUSCAR comandos.
  Usa a chave de ingestão.
- A consola de controlo CRIA comandos e retreina o modelo.
  Usa a chave de controlo, que o dashboard de monitorização não tem.
- As leituras de monitorização são só de leitura. Num ambiente real ficam
  atrás de uma camada de acesso, como o Cloudflare Access.
"""
from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import classificar_pressao, get_settings
from app.database import get_db, init_db
from app.ml_engine import MLEngine
from app.models import ComandoModel, TelemetriaModel
from app.schemas import (
    ComandoConfirmacao,
    ComandoIn,
    ComandoOut,
    InfoSistema,
    ResumoPoco,
    TelemetriaIn,
    TelemetriaOut,
)

DB = Annotated[Session, Depends(get_db)]


def _verificar_chave(recebida: str | None, esperada: str) -> None:
    if recebida is None or not hmac.compare_digest(recebida, esperada):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave de API inválida ou em falta.")


def exige_ingestao(x_api_key: Annotated[str | None, Header()] = None) -> None:
    _verificar_chave(x_api_key, get_settings().chave_ingestao)


def exige_controlo(x_api_key: Annotated[str | None, Header()] = None) -> None:
    _verificar_chave(x_api_key, get_settings().chave_controlo)


def create_app() -> FastAPI:
    ml = MLEngine()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(get_settings().db_url)
        yield

    app = FastAPI(
        title="Digital Twin — Telemetria Offshore",
        description="Telemetria, comandos auditados e deteção de anomalias para poços offshore (dados simulados ou Volve).",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.state.ml = ml

    # ---------------------------------------------------------------- sistema
    @app.get("/health", tags=["sistema"])
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/info", response_model=InfoSistema, tags=["sistema"])
    def info() -> InfoSistema:
        s = get_settings()
        return InfoSistema(
            modo_dados=s.modo_dados,
            limite_atencao_bar=s.limite_atencao,
            limite_critico_bar=s.limite_critico,
            preco_barril_usd=s.preco_barril_usd,
            modelo_ml_treinado=ml.treinado,
        )

    # ------------------------------------------------------------- telemetria
    @app.post(
        "/api/telemetria",
        response_model=TelemetriaOut,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(exige_ingestao)],
        tags=["campo"],
    )
    def receber_telemetria(dado: TelemetriaIn, db: DB) -> TelemetriaModel:
        ts = dado.timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        registo = TelemetriaModel(
            poco_id=dado.poco_id,
            timestamp=ts,
            pressao_bar=dado.pressao_bar,
            temperatura_celsius=dado.temperatura_celsius,
            caudal_oleo_m3h=dado.caudal_oleo_m3h,
            abertura_choke_pct=dado.abertura_choke_pct,
            status_seguranca=classificar_pressao(dado.pressao_bar),
            anomalia_ml=ml.e_anomalia(dado.pressao_bar, dado.temperatura_celsius, dado.caudal_oleo_m3h),
            fonte=dado.fonte,
        )
        db.add(registo)
        db.commit()
        db.refresh(registo)
        return registo

    @app.get("/api/historico", response_model=list[TelemetriaOut], tags=["monitorização"])
    def historico(
        db: DB,
        poco_id: str | None = None,
        limit: Annotated[int, Query(ge=1, le=5000)] = 500,
    ) -> list[TelemetriaModel]:
        consulta = select(TelemetriaModel)
        if poco_id:
            consulta = consulta.where(TelemetriaModel.poco_id == poco_id)
        consulta = consulta.order_by(TelemetriaModel.id.desc()).limit(limit)
        return list(reversed(db.scalars(consulta).all()))

    @app.get("/api/pocos", response_model=list[ResumoPoco], tags=["monitorização"])
    def pocos(db: DB) -> list[ResumoPoco]:
        ultimos = select(func.max(TelemetriaModel.id)).group_by(TelemetriaModel.poco_id)
        linhas = db.scalars(select(TelemetriaModel).where(TelemetriaModel.id.in_(ultimos))).all()
        return [
            ResumoPoco(
                poco_id=l.poco_id,
                ultima_leitura=l.timestamp,
                pressao_bar=l.pressao_bar,
                status_seguranca=l.status_seguranca,
                fonte=l.fonte,
            )
            for l in sorted(linhas, key=lambda l: l.poco_id)
        ]

    # --------------------------------------------------------------- comandos
    @app.post(
        "/api/comando",
        response_model=ComandoOut,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(exige_controlo)],
        tags=["controlo"],
    )
    def criar_comando(comando: ComandoIn, db: DB) -> ComandoModel:
        if get_settings().modo_dados == "volve":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Modo Volve: os dados são um replay histórico e não aceitam comandos.",
            )
        existe = db.scalar(select(TelemetriaModel.id).where(TelemetriaModel.poco_id == comando.poco_id).limit(1))
        if existe is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Poço '{comando.poco_id}' desconhecido.")
        registo = ComandoModel(poco_id=comando.poco_id, acao=comando.acao, operador=comando.operador)
        db.add(registo)
        db.commit()
        db.refresh(registo)
        return registo

    @app.get("/api/comandos", response_model=list[ComandoOut], tags=["monitorização"])
    def listar_comandos(db: DB, limit: Annotated[int, Query(ge=1, le=500)] = 50) -> list[ComandoModel]:
        return list(db.scalars(select(ComandoModel).order_by(ComandoModel.id.desc()).limit(limit)).all())

    @app.get(
        "/api/comandos/pendentes",
        response_model=list[ComandoOut],
        dependencies=[Depends(exige_ingestao)],
        tags=["campo"],
    )
    def comandos_pendentes(db: DB) -> list[ComandoModel]:
        return list(
            db.scalars(select(ComandoModel).where(ComandoModel.estado == "PENDENTE").order_by(ComandoModel.id)).all()
        )

    @app.post(
        "/api/comandos/{comando_id}/confirmacao",
        response_model=ComandoOut,
        dependencies=[Depends(exige_ingestao)],
        tags=["campo"],
    )
    def confirmar_comando(comando_id: int, confirmacao: ComandoConfirmacao, db: DB) -> ComandoModel:
        registo = db.get(ComandoModel, comando_id)
        if registo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comando não encontrado.")
        if registo.estado != "PENDENTE":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Comando já está {registo.estado}.")
        registo.estado = confirmacao.estado
        registo.detalhe = confirmacao.detalhe
        registo.executado_em = datetime.now(timezone.utc)
        db.commit()
        db.refresh(registo)
        return registo

    # --------------------------------------------------------------------- ML
    @app.post("/api/ml/retreinar", dependencies=[Depends(exige_controlo)], tags=["controlo"])
    def retreinar(db: DB) -> dict:
        resultado = ml.retreinar(db)
        if not resultado["sucesso"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=resultado["mensagem"])
        return resultado

    return app


app = create_app()
