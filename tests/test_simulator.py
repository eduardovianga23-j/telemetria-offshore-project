"""O campo aplica os comandos que vai buscar à API, de ponta a ponta."""
from app.physics import POCOS_ANGOLA, EstadoPoco
from app.simulator import ciclo_simulacao
from tests.conftest import CONTROLO, INGESTAO


class ClienteTeste:
    """Adapta o TestClient do FastAPI à interface do ClienteAPI."""

    def __init__(self, client):
        self.c = client

    def enviar(self, leitura):
        self.c.post("/api/telemetria", json=leitura, headers=INGESTAO).raise_for_status()

    def pendentes(self):
        return self.c.get("/api/comandos/pendentes", headers=INGESTAO).json()

    def confirmar(self, comando_id, estado, detalhe):
        self.c.post(
            f"/api/comandos/{comando_id}/confirmacao", json={"estado": estado, "detalhe": detalhe}, headers=INGESTAO
        ).raise_for_status()


def test_comando_chega_ao_poco_e_fica_auditado(client):
    cliente = ClienteTeste(client)
    estados = {p.poco_id: EstadoPoco.novo(p, seed=1) for p in POCOS_ANGOLA}

    ciclo_simulacao(cliente, estados)  # primeiras leituras
    client.post("/api/comando", json={"poco_id": "B32-C", "acao": "ALIVIAR_PRESSAO"}, headers=CONTROLO)
    ciclo_simulacao(cliente, estados)  # o campo vai buscar o comando e aplica-o

    assert estados["B32-C"].alivio_ativo
    assert not estados["B17-A"].alivio_ativo
    registo = client.get("/api/comandos").json()[0]
    assert registo["estado"] == "EXECUTADO" and registo["executado_em"] is not None
