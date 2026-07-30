import os
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session
from typing import Optional
from app.models import TelemetriaModel  # ✅ Corrigido para corresponder ao main.py

MODEL_PATH = "modelo_anomaly.pkl"

class MLEngine:
    def __init__(self):
        self.features = ["pressao_bar", "temperatura_celsius", "vazao_m3h"]
        self.model = self._carregar_ou_criar_modelo()

    def _carregar_ou_criar_modelo(self):
        """Carrega o modelo guardado em disco ou inicializa um novo."""
        if os.path.exists(MODEL_PATH):
            try:
                return joblib.load(MODEL_PATH)
            except Exception:
                pass
        
        # Modelo base com 5% de taxa esperada de contaminação/anomalias
        model = IsolationForest(contamination=0.05, random_state=42)
        return model

    def retreinar_modelo(self, db: Session) -> dict:
        """
        Lê todas as leituras da base de dados, retreina o Isolation Forest
        e guarda o modelo atualizado em disco.
        """
        # ✅ Consulta corrigida para usar TelemetriaModel
        leituras = db.query(TelemetriaModel).all()
        
        if len(leituras) < 10:
            return {
                "sucesso": False,
                "mensagem": f"Dados insuficientes para retreino (mínimo 10 leituras, atual: {len(leituras)})"
            }

        # Converter registos da BD para DataFrame do Pandas
        data = [{
            "pressao_bar": l.pressao_bar,
            "temperatura_celsius": l.temperatura_celsius,
            "vazao_m3h": l.vazao_m3h if l.vazao_m3h is not None else 400.0
        } for l in leituras]
        
        df = pd.DataFrame(data)

        # Ajustar/Treinar o modelo
        self.model.fit(df[self.features])
        
        # Guardar o modelo em ficheiro binário
        joblib.dump(self.model, MODEL_PATH)

        # Avaliar previsões no dataset de treino
        previsoes = self.model.predict(df[self.features]) # -1 = Anomalia, 1 = Normal
        anomalias_detetadas = int((previsoes == -1).sum())

        return {
            "sucesso": True,
            "mensagem": "Modelo retreinado com sucesso!",
            "total_amostras": len(df),
            "anomalias_encontradas": anomalias_detetadas,
            "taxa_anomalias_pct": round((anomalias_detetadas / len(df)) * 100, 2)
        }

    def prever_anomalia(self, pressao: float, temp: float, vazao: Optional[float] = None) -> bool:
        """
        Retorna True se os dados do sensor forem considerados anómalos pelo modelo.
        """
        vazao_val = vazao if vazao is not None else 400.0

        if not hasattr(self.model, "estimators_"):
            # Se o modelo ainda não foi treinado com fit(), usa regra de segurança simples
            return pressao > 150.0 or temp > 85.0

        df = pd.DataFrame([[pressao, temp, vazao_val]], columns=self.features)
        pred = self.model.predict(df)[0]
        return pred == -1

# Instância global do motor de ML
ml_engine = MLEngine()