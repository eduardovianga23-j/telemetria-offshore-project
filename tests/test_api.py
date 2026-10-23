import pytest

from tests.conftest import CONTROLO, INGESTAO, leitura


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("pressao,esperado", [(120.0, "OK"), (140.0, "ATENÇÃO"), (155.0, "CRÍTICO")])
def test_api_classifica_pressao(client, pressao, esperado):
    r = client.post("/api/telemetria", json=leitura(pressao=pressao), headers=INGESTAO)
    assert r.status_code == 201
    assert r.json()["status_seguranca"] == esperado


def test_emissor_nao_pode_impor_estado(client):
    # O campo não decide o estado de segurança: um estado enviado é ignorado
    r = client.post("/api/telemetria", json=leitura(pressao=160.0, status_seguranca="OK"), headers=INGESTAO)
    assert r.json()["status_seguranca"] == "CRÍTICO"


def test_telemetria_exige_chave(client):
    assert client.post("/api/telemetria", json=leitura()).status_code == 401
    assert client.post("/api/telemetria", json=leitura(), headers=CONTROLO).status_code == 401


def test_telemetria_rejeita_valores_impossiveis(client):
    assert client.post("/api/telemetria", json=leitura(pressao=-5), headers=INGESTAO).status_code == 422


def test_historico_filtra_por_poco_e_mantem_ordem(client):
    for i, poco in enumerate(["B17-A", "B32-C", "B17-A"]):
        client.post("/api/telemetria", json=leitura(poco=poco, pressao=110 + i), headers=INGESTAO)
    dados = client.get("/api/historico", params={"poco_id": "B17-A"}).json()
    assert [d["pressao_bar"] for d in dados] == [110, 112]
    assert {p["poco_id"] for p in client.get("/api/pocos").json()} == {"B17-A", "B32-C"}


def test_comando_exige_chave_de_controlo(client):
    client.post("/api/telemetria", json=leitura(), headers=INGESTAO)
    cmd = {"poco_id": "B17-A", "acao": "ALIVIAR_PRESSAO"}
    assert client.post("/api/comando", json=cmd).status_code == 401
    assert client.post("/api/comando", json=cmd, headers=INGESTAO).status_code == 401
    assert client.post("/api/comando", json=cmd, headers=CONTROLO).status_code == 202


def test_comando_para_poco_desconhecido(client):
    r = client.post("/api/comando", json={"poco_id": "XPTO", "acao": "ALIVIAR_PRESSAO"}, headers=CONTROLO)
    assert r.status_code == 404


def test_comando_nao_altera_historico(client):
    client.post("/api/telemetria", json=leitura(pressao=158.0), headers=INGESTAO)
    client.post("/api/comando", json={"poco_id": "B17-A", "acao": "ALIVIAR_PRESSAO"}, headers=CONTROLO)
    assert client.get("/api/historico").json()[-1]["pressao_bar"] == 158.0


def test_ciclo_de_vida_do_comando(client):
    client.post("/api/telemetria", json=leitura(), headers=INGESTAO)
    criado = client.post("/api/comando", json={"poco_id": "B17-A", "acao": "ALIVIAR_PRESSAO"}, headers=CONTROLO).json()
    assert criado["estado"] == "PENDENTE"

    pendentes = client.get("/api/comandos/pendentes", headers=INGESTAO).json()
    assert [c["id"] for c in pendentes] == [criado["id"]]

    r = client.post(f"/api/comandos/{criado['id']}/confirmacao", json={"estado": "EXECUTADO"}, headers=INGESTAO)
    assert r.json()["estado"] == "EXECUTADO"
    assert client.get("/api/comandos/pendentes", headers=INGESTAO).json() == []

    # Não se confirma duas vezes
    r = client.post(f"/api/comandos/{criado['id']}/confirmacao", json={"estado": "EXECUTADO"}, headers=INGESTAO)
    assert r.status_code == 409


def test_modo_volve_recusa_comandos(client, monkeypatch):
    client.post("/api/telemetria", json=leitura(), headers=INGESTAO)
    monkeypatch.setenv("MODO_DADOS", "volve")
    r = client.post("/api/comando", json={"poco_id": "B17-A", "acao": "ALIVIAR_PRESSAO"}, headers=CONTROLO)
    assert r.status_code == 409


def test_retreino_e_deteccao_de_anomalias(client):
    assert client.post("/api/ml/retreinar", headers=CONTROLO).status_code == 400  # sem dados

    from app.physics import POCOS_ANGOLA, EstadoPoco

    estado = EstadoPoco.novo(POCOS_ANGOLA[0], seed=7)
    for _ in range(120):
        client.post("/api/telemetria", json=estado.passo(), headers=INGESTAO)

    r = client.post("/api/ml/retreinar", headers=CONTROLO)
    assert r.status_code == 200 and r.json()["total_amostras"] == 120
    assert client.get("/api/info").json()["modelo_ml_treinado"] is True

    normal = client.post("/api/telemetria", json=estado.passo(), headers=INGESTAO).json()
    estranha = client.post(
        "/api/telemetria", json=leitura(pressao=124.0, caudal_oleo_m3h=5.0, temperatura_celsius=40.0), headers=INGESTAO
    ).json()
    assert normal["anomalia_ml"] is False
    assert estranha["anomalia_ml"] is True
    assert estranha["status_seguranca"] == "OK"  # a regra de limite não a apanha; o modelo sim
