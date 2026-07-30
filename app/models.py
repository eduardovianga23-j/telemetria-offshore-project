from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from app.database import Base

class TelemetriaModel(Base):
    __tablename__ = "telemetria"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    poco_id = Column(String, index=True)
    pressao_bar = Column(Float)
    temperatura_celsius = Column(Float)
    vazao_m3h = Column(Float, nullable=True)
    status_seguranca = Column(String)  # ex: "OK", "ATENÇÃO", "CRÍTICO"
    timestamp = Column(DateTime, default=datetime.utcnow)