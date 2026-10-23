"""Configuração central do sistema.

Todos os valores vêm de variáveis de ambiente, com valores por defeito
seguros para desenvolvimento. Assim, o mesmo código corre no portátil,
no Docker Compose e, mais tarde, na cloud, sem alterações.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

M3_POR_BARRIL = 0.158987  # 1 barril = 0,158987 m³


def _float(nome: str, defeito: float) -> float:
    return float(os.getenv(nome, defeito))


@dataclass(frozen=True)
class Settings:
    # Base de dados
    db_url: str

    # Chaves de API (cabeçalho X-API-Key)
    chave_ingestao: str  # usada pelo simulador / gateway de campo
    chave_controlo: str  # usada só pela consola de controlo

    # Limites operacionais (bar)
    limite_atencao: float
    limite_critico: float

    # Economia
    preco_barril_usd: float

    # Modo de dados: "simulacao" (Blocos 17 e 32) ou "volve" (replay real)
    modo_dados: str

    @property
    def preco_m3_usd(self) -> float:
        return self.preco_barril_usd / M3_POR_BARRIL


def get_settings() -> Settings:
    """Lê a configuração no momento da chamada (facilita os testes)."""
    return Settings(
        db_url=os.getenv("DB_URL", "sqlite:///./telemetria.db"),
        chave_ingestao=os.getenv("API_KEY_INGESTAO", "dev-ingestao"),
        chave_controlo=os.getenv("API_KEY_CONTROLO", "dev-controlo"),
        limite_atencao=_float("LIMITE_ATENCAO_BAR", 135.0),
        limite_critico=_float("LIMITE_CRITICO_BAR", 150.0),
        preco_barril_usd=_float("PRECO_BARRIL_USD", 80.0),
        modo_dados=os.getenv("MODO_DADOS", "simulacao").lower(),
    )


def classificar_pressao(pressao_bar: float, s: Settings | None = None) -> str:
    """Regra de segurança única, usada pela API e pelo dashboard."""
    s = s or get_settings()
    if pressao_bar > s.limite_critico:
        return "CRÍTICO"
    if pressao_bar > s.limite_atencao:
        return "ATENÇÃO"
    return "OK"
