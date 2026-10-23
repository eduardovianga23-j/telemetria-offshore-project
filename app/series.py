"""Preparação de séries temporais para os gráficos."""
from __future__ import annotations

import pandas as pd


def com_quebras(df: pd.DataFrame, coluna: str, limiar: pd.Timedelta) -> tuple[list, list]:
    """Devolve (x, y) com um ponto vazio onde há um intervalo maior do que o limiar.

    Assim o gráfico não liga com uma reta dois pontos separados por meses
    (por exemplo, um poço que esteve parado), o que seria enganador.
    """
    g = df.sort_values("timestamp")
    xs: list = []
    ys: list = []
    anterior = None
    for ts, valor in zip(g["timestamp"], g[coluna]):
        if anterior is not None and ts - anterior > limiar:
            xs.append(None)
            ys.append(None)
        xs.append(ts)
        ys.append(valor)
        anterior = ts
    return xs, ys
