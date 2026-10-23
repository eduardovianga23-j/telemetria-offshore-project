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


def test_replay_retoma_onde_parou():
    from app.simulator import dias_por_enviar

    def dia(d, *pocos):
        return [{"timestamp": f"2014-01-0{d}T00:00:00+00:00", "poco_id": p} for p in pocos]

    dias = [dia(1, "A", "B"), dia(2, "A", "B"), dia(3, "A", "B")]
    # Sem histórico: envia tudo
    assert len(list(dias_por_enviar(dias, {"ultimo_timestamp": None}))) == 3
    # Parou a meio do dia 2 (só o A chegou): envia o B do dia 2 e o dia 3
    restantes = list(dias_por_enviar(dias, {"ultimo_timestamp": "2014-01-02T00:00:00+00:00", "pocos_no_ultimo": ["A"]}))
    assert [[l["poco_id"] for l in d] for d in restantes] == [["B"], ["A", "B"]]
    # Dia 3 já completo: nada a enviar
    assert list(dias_por_enviar(dias, {"ultimo_timestamp": "2014-01-03T00:00:00+00:00", "pocos_no_ultimo": ["A", "B"]})) == []
