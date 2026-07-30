from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

app = FastAPI(
    title="Digital Twin - API Offshore",
    description="API REST para receção de telemetria, comandos remotos e MLOps",
    version="1.0.0"
)

db_telemetria: List[dict] = []

class TelemetriaInput(BaseModel):
    poco_id: str = Field(..., json_schema_extra={"example": "POCO-01"})
    pressao_bar: float = Field(..., json_schema_extra={"example": 120.5})
    temperatura_celsius: float = Field(..., json_schema_extra={"example": 65.2})
    vazao_m3h: Optional[float] = Field(default=0.0, json_schema_extra={"example": 45.0})
    status_seguranca: Optional[str] = Field(default="OK", json_schema_extra={"example": "OK"})
    timestamp: Optional[str] = Field(default=None)

class ComandoInput(BaseModel):
    poco_id: str = Field(..., json_schema_extra={"example": "POCO-01"})
    acao: str = Field(..., json_schema_extra={"example": "ALIVIAR_PRESSAO"})

@app.get("/")
def root():
    return {"status": "online", "message": "API Offshore Digital Twin a rodar com sucesso!"}

@app.post("/api/telemetria", status_code=status.HTTP_201_CREATED)
def receber_telemetria(dado: TelemetriaInput):
    registro = dado.model_dump()  # Compatível com Pydantic v2
    if not registro.get("timestamp"):
        registro["timestamp"] = datetime.now().isoformat()
    
    if registro["pressao_bar"] > 150.0:
        registro["status_seguranca"] = "CRÍTICO"
    elif registro["pressao_bar"] > 135.0:
        registro["status_seguranca"] = "ATENÇÃO"
    
    db_telemetria.append(registro)
    
    if len(db_telemetria) > 1000:
        db_telemetria.pop(0)
        
    return {"message": "Telemetria recebida com sucesso", "registro": registro}

@app.get("/api/historico")
def obter_historico():
    return db_telemetria

@app.post("/api/comando")
def enviar_comando(comando: ComandoInput):
    poco = comando.poco_id
    acao = comando.acao
    
    for item in reversed(db_telemetria):
        if item["poco_id"] == poco:
            item["pressao_bar"] = max(100.0, item["pressao_bar"] - 30.0)
            item["status_seguranca"] = "OK"
            break
            
    return {
        "status": "sucesso",
        "mensagem": f"Comando '{acao}' executado com sucesso no poço {poco}."
    }

@app.post("/api/ml/retreinar")
def retreinar_modelo():
    total = len(db_telemetria)
    if total < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dados insuficientes na Base de Dados para treinar o modelo (mínimo 5 registos)."
        )
    
    anomalias = sum(1 for item in db_telemetria if item.get("status_seguranca") in ["CRÍTICO", "ATENÇÃO"])
    taxa = round((anomalias / total) * 100, 2)
    
    return {
        "status": "concluido",
        "total_amostras": total,
        "anomalias_encontradas": anomalias,
        "taxa_anomalias_pct": taxa
    }