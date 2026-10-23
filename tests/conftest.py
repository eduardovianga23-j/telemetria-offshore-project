import pytest
from fastapi.testclient import TestClient

INGESTAO = {"X-API-Key": "teste-ingestao"}
CONTROLO = {"X-API-Key": "teste-controlo"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_URL", f"sqlite:///{tmp_path / 'teste.db'}")
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "modelo.joblib"))
    monkeypatch.setenv("API_KEY_INGESTAO", "teste-ingestao")
    monkeypatch.setenv("API_KEY_CONTROLO", "teste-controlo")
    monkeypatch.setenv("MODO_DADOS", "simulacao")

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def leitura(poco="B17-A", pressao=120.0, **extra):
    return {
        "poco_id": poco,
        "pressao_bar": pressao,
        "temperatura_celsius": 78.0,
        "caudal_oleo_m3h": 95.0,
        "abertura_choke_pct": 45.0,
        **extra,
    }
