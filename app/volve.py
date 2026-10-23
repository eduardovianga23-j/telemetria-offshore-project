"""Leitor dos dados reais de produção do campo Volve (Equinor).

Os dados NÃO estão incluídos neste repositório: a licença da Equinor exige
atribuição, uso não comercial e partilha nas mesmas condições. Cada pessoa
descarrega o ficheiro de produção diretamente da Equinor e indica o caminho
na variável VOLVE_FICHEIRO (CSV ou Excel).

Os dados são diários. O simulador faz "replay": envia um dia de produção
real a cada passo, com a data original.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import timezone
from pathlib import Path

import pandas as pd

# Colunas do ficheiro de produção diária do Volve
COLUNAS = {
    "data": "DATEPRD",
    "poco": "NPD_WELL_BORE_NAME",
    "horas": "ON_STREAM_HRS",
    "pressao": "AVG_WHP_P",  # pressão na cabeça do poço (bar)
    "temperatura": "AVG_WHT_P",  # temperatura na cabeça do poço (°C)
    "choke": "AVG_CHOKE_SIZE_P",  # abertura do choke (%)
    "oleo": "BORE_OIL_VOL",  # petróleo produzido no dia (Sm³)
    "tipo_fluxo": "FLOW_KIND",
}

ATRIBUICAO = (
    "Dados de produção: campo Volve, Equinor e parceiros da licença, "
    "disponibilizados sob a Equinor Open Data Licence."
)


class ErroVolve(ValueError):
    pass


def _ler_ficheiro(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise ErroVolve(
            f"Ficheiro Volve não encontrado em '{caminho}'. Descarregue-o da Equinor "
            "e defina VOLVE_FICHEIRO (ver README)."
        )
    if caminho.suffix.lower() in {".xlsx", ".xls"}:
        folhas = pd.read_excel(caminho, sheet_name=None)
        # A folha diária é a que tem a coluna de data diária
        for df in folhas.values():
            if COLUNAS["data"] in df.columns:
                return df
        raise ErroVolve(f"Nenhuma folha de '{caminho.name}' tem a coluna {COLUNAS['data']}.")
    return pd.read_csv(caminho)


def carregar_producao(caminho: str | Path) -> pd.DataFrame:
    """Devolve as leituras diárias válidas, já no formato da API, ordenadas por data."""
    df = _ler_ficheiro(Path(caminho))

    obrigatorias = [COLUNAS[k] for k in ("data", "poco", "horas", "pressao", "temperatura", "oleo")]
    em_falta = [c for c in obrigatorias if c not in df.columns]
    if em_falta:
        raise ErroVolve(f"Colunas em falta no ficheiro Volve: {', '.join(em_falta)}")

    if COLUNAS["tipo_fluxo"] in df.columns:
        df = df[df[COLUNAS["tipo_fluxo"]].astype(str).str.lower() == "production"]

    df = df[(df[COLUNAS["horas"]] > 0) & (df[COLUNAS["oleo"]] > 0)]
    df = df.dropna(subset=[COLUNAS["pressao"], COLUNAS["temperatura"]])

    saida = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(df[COLUNAS["data"]], dayfirst=True).dt.tz_localize(timezone.utc),
            "poco_id": df[COLUNAS["poco"]].astype(str).str.strip(),
            "pressao_bar": df[COLUNAS["pressao"]].astype(float).round(2),
            "temperatura_celsius": df[COLUNAS["temperatura"]].astype(float).round(2),
            # Caudal médio enquanto o poço esteve em produção
            "caudal_oleo_m3h": (df[COLUNAS["oleo"]] / df[COLUNAS["horas"]]).astype(float).round(2),
            "abertura_choke_pct": (
                df[COLUNAS["choke"]].astype(float).clip(0, 100).round(1)
                if COLUNAS["choke"] in df.columns
                else None
            ),
        }
    )
    saida["fonte"] = "volve"
    return saida.sort_values(["timestamp", "poco_id"]).reset_index(drop=True)


def dias_de_producao(df: pd.DataFrame) -> Iterator[list[dict]]:
    """Agrupa as leituras por dia, pela ordem real, para o replay."""
    for ts, grupo in df.groupby("timestamp", sort=True):
        leituras = []
        for linha in grupo.to_dict("records"):
            linha["timestamp"] = pd.Timestamp(ts).isoformat()
            if linha.get("abertura_choke_pct") is not None and pd.isna(linha["abertura_choke_pct"]):
                linha["abertura_choke_pct"] = None
            leituras.append(linha)
        yield leituras
