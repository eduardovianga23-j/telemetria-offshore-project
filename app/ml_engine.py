import os
import joblib
import pandas as pd
from typing import Optional
from sqlalchemy.orm import Session
from sklearn.ensemble import IsolationForest
from app.models import TelemetriaModel  # ✅ Modelo SQLAlchemy da BD

# Guarda o modelo numa pasta dedicada 'models/' para melhor organização e Docker
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "modelo_anomaly.pkl")


class MLEngine:
    def __init__(self):
        self.features = ["pressao_bar", "temperatura_celsius", "vazao_m3h"]
        self.model = self._carregar_ou_criar_modelo()

    def _carregar_ou_criar_modelo(self) -> IsolationForest:
        """
        Carrega o modelo guardado em disco se ele existir e estiver treinado.
        Caso contrário, inicializa uma nova instância do IsolationForest.
        """
        if os.path.exists(MODEL_PATH):
            try:
                modelo_carregado = joblib.load(MODEL_PATH)
                # Verifica se o modelo carregado já passou por um .fit()
                if hasattr(modelo_carregado, "estimators_"):
                    print(f"✅ [ML Engine] Modelo de Machine Learning carregado com sucesso de '{MODEL_PATH}'.")
                    return modelo_carregado
            except Exception as e:
                print(f"⚠️ [ML Engine] Erro ao carregar modelo guardado ({e}). Criando um novo modelo base.")

        # Modelo base com 5% de taxa esperada de contaminação/anomalias
        print("ℹ️ [ML Engine] Inicializando novo modelo IsolationForest (não treinado).")
        return IsolationForest(contamination=0.05, random_state=42)

    def retreinar_modelo(self, db: Session) -> dict:
        """
        Lê todas as leituras da base de dados, retreina o Isolation Forest
        e guarda o modelo atualizado em disco com persitência (joblib).
        """
        # Consulta todas as leituras de telemetria
        leituras = db.query(TelemetriaModel).all()

        if len(leituras) < 10:
            return {
                "sucesso": False,
                "mensagem": f"Dados insuficientes para retreino (mínimo 10 leituras necessárias, atual: {len(leituras)})"
            }

        # Converter registos da BD para DataFrame do Pandas com fallback seguro para vazão
        data = [{
            "pressao_bar": float(l.pressao_bar),
            "temperatura_celsius": float(l.temperatura_celsius),
            "vazao_m3h": float(l.vazao_m3h) if l.vazao_m3h is not None else 400.0
        } for l in leituras]

        df = pd.DataFrame(data)

        # Retreinar o modelo com os novos dados
        self.model.fit(df[self.features])

        # Garantir que a pasta de modelos existe antes de guardar
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(self.model, MODEL_PATH)
        print(f"💾 [ML Engine] Modelo atualizado e guardado em '{MODEL_PATH}'.")

        # Avaliar previsões no dataset de treino
        previsoes = self.model.predict(df[self.features])  # -1 = Anomalia, 1 = Normal
        anomalias_detetadas = int((previsoes == -1).sum())

        return {
            "sucesso": True,
            "mensagem": "Modelo retreinado e guardado com sucesso!",
            "total_amostras": len(df),
            "anomalias_encontradas": anomalias_detetadas,
            "taxa_anomalias_pct": round((anomalias_detetadas / len(df)) * 100, 2)
        }

    def prever_anomalia(self, pressao: float, temp: float, vazao: Optional[float] = None) -> bool:
        """
        Retorna True se os dados do sensor forem considerados anómalos pelo modelo ML.
        Se o modelo ainda não tiver sido treinado, utiliza a regra heurística de segurança.
        """
        vazao_val = float(vazao) if vazao is not None else 400.0

        # Se o modelo ainda não foi treinado com fit(), usa regra de segurança padrão
        if not hasattr(self.model, "estimators_"):
            return pressao > 150.0 or temp > 85.0

        df = pd.DataFrame([[pressao, temp, vazao_val]], columns=self.features)
        pred = self.model.predict(df)[0]
        return pred == -1


# Instância global do motor de ML
ml_engine = MLEngine()