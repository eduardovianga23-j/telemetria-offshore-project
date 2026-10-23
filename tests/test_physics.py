import pytest

from app.physics import POCOS_ANGOLA, EstadoPoco


@pytest.fixture
def poco():
    return EstadoPoco.novo(POCOS_ANGOLA[0], seed=42)


def test_pressao_tem_inercia(poco):
    pressoes = [poco.passo()["pressao_bar"] for _ in range(500)]
    saltos = [abs(a - b) for a, b in zip(pressoes, pressoes[1:])]
    assert max(saltos) < 10  # sem saltos impossíveis entre leituras


def test_valores_plausiveis(poco):
    for _ in range(500):
        l = poco.passo()
        assert 20 < l["pressao_bar"] < 200
        assert 0 < l["caudal_oleo_m3h"] < 300
        assert 40 < l["temperatura_celsius"] < 120


def test_alivio_baixa_pressao_gradualmente(poco):
    for _ in range(50):
        poco.passo()
    poco.pico_bar = 40  # força um pico
    for _ in range(15):
        poco.passo()
    antes = poco.pressao_bar
    poco.aplicar_comando("ALIVIAR_PRESSAO")
    seguintes = [poco.passo()["pressao_bar"] for _ in range(10)]
    assert seguintes[0] > antes - 15  # não cai de uma vez
    assert seguintes[-1] < antes - 20  # mas desce de forma clara


def test_alivio_desvia_caudal(poco):
    for _ in range(30):
        poco.passo()
    caudal_antes = poco.passo()["caudal_oleo_m3h"]
    poco.aplicar_comando("ALIVIAR_PRESSAO")
    assert poco.passo()["caudal_oleo_m3h"] < caudal_antes * 0.85


def test_repor_normal_fecha_alivio(poco):
    poco.aplicar_comando("ALIVIAR_PRESSAO")
    poco.aplicar_comando("REPOR_NORMAL")
    assert not poco.alivio_ativo


def test_acao_desconhecida(poco):
    with pytest.raises(ValueError):
        poco.aplicar_comando("ABRIR_TUDO")
