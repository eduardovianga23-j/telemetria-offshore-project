"""Deteção de anomalias com Isolation Forest.

O modelo aprende o comportamento habitual do conjunto pressão, temperatura e
caudal, e marca as leituras invulgares. Complementa as regras de limite:
uma regra só vê "pressão acima de 150 bar", o modelo também apanha
combinações estranhas, como pressão normal com caudal muito baixo.
"""
from __future__ import annotations

import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TelemetriaModel

FEATURES = ["pressao_bar", "temperatura_celsius", "caudal_oleo_m3h"]
MINIMO_AMOSTRAS = 50
MAX_AMOSTRAS_TREINO = 20_000


class MLEngine:
    def __init__(self, caminho_modelo: str | None = None):
        self.caminho = Path(caminho_modelo or os.getenv("MODEL_PATH", "models/modelo_anomalias.joblib"))
        self.model: IsolationForest | None = self._carregar()

    @property
    def treinado(self) -> bool:
        return self.model is not None

    def _carregar(self) -> IsolationForest | None:
        if self.caminho.exists():
            try:
                modelo = joblib.load(self.caminho)
                if hasattr(modelo, "estimators_"):
                    return modelo
            except Exception as e:  # ficheiro corrompido ou de outra versão
                print(f"[ML] Não foi possível carregar o modelo ({e}); será preciso retreinar.")
        return None

    def retreinar(self, db: Session) -> dict:
        consulta = (
            select(TelemetriaModel.pressao_bar, TelemetriaModel.temperatura_celsius, TelemetriaModel.caudal_oleo_m3h)
            .order_by(TelemetriaModel.id.desc())
            .limit(MAX_AMOSTRAS_TREINO)
        )
        df = pd.DataFrame(db.execute(consulta).all(), columns=FEATURES)
        if len(df) < MINIMO_AMOSTRAS:
            return {
                "sucesso": False,
                "mensagem": f"Dados insuficientes: são precisas {MINIMO_AMOSTRAS} leituras, existem {len(df)}.",
            }

        modelo = IsolationForest(n_estimators=200, contamination=0.03, random_state=42)
        modelo.fit(df[FEATURES])
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(modelo, self.caminho)
        self.model = modelo

        anomalias = int((modelo.predict(df[FEATURES]) == -1).sum())
        return {
            "sucesso": True,
            "mensagem": "Modelo retreinado e guardado.",
            "total_amostras": len(df),
            "anomalias_encontradas": anomalias,
            "taxa_anomalias_pct": round(anomalias / len(df) * 100, 2),
        }

    def e_anomalia(self, pressao: float, temperatura: float, caudal: float) -> bool | None:
        """True/False se o modelo estiver treinado; None se ainda não houver modelo."""
        if self.model is None:
            return None
        df = pd.DataFrame([[pressao, temperatura, caudal]], columns=FEATURES)
        return bool(self.model.predict(df)[0] == -1)
