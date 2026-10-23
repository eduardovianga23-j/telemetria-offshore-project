from app.i18n import COLUNAS, TEXTOS, VALORES, t, v


def test_idiomas_tem_as_mesmas_chaves():
    assert TEXTOS["en"].keys() == TEXTOS["pt"].keys()
    assert COLUNAS["en"].keys() == COLUNAS["pt"].keys()


def test_textos_com_valores():
    assert t("alerta_critico", "en", poco="B17-A", p=151.24, lim=150) == "CRITICAL ALERT — B17-A: 151.2 bar (limit 150 bar)"
    assert t("alerta_critico", "pt", poco="B17-A", p=151.24, lim=150) == "ALERTA CRÍTICO — B17-A: 151.2 bar (limite 150 bar)"


def test_valores_da_api():
    assert v("CRÍTICO", "en") == "CRITICAL" and v("CRÍTICO", "pt") == "CRÍTICO"
    assert v("EXECUTADO", "en") == "EXECUTED"
    assert v("desconhecido", "en") == "desconhecido"


def test_idioma_invalido_usa_ingles(monkeypatch):
    monkeypatch.setenv("IDIOMA", "fr")
    assert t("btn_aliviar") == "Relieve pressure"


def test_todos_os_textos_formatam(monkeypatch):
    exemplo = dict(url="x", erro="e", atencao=1, critico=2, preco=80, amostras=1, anomalias=0, taxa=0,
                   v=1.0, acao="A", poco="P", p=1.0, lim=2, estado="E")
    for idioma in ("en", "pt"):
        for chave in TEXTOS[idioma]:
            t(chave, idioma, **exemplo)
    assert VALORES["pt"] == {}
