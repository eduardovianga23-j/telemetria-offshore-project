"""Testes do leitor Volve com um ficheiro sintético (os dados reais não vão para o Git)."""
import pandas as pd
import pytest

from app.volve import ErroVolve, carregar_producao, dias_de_producao


def escrever(tmp_path, linhas, nome="volve.csv"):
    caminho = tmp_path / nome
    df = pd.DataFrame(linhas)
    if nome.endswith(".xlsx"):
        with pd.ExcelWriter(caminho) as w:
            pd.DataFrame({"x": [1]}).to_excel(w, sheet_name="Monthly", index=False)
            df.to_excel(w, sheet_name="Daily Production Data", index=False)
    else:
        df.to_csv(caminho, index=False)
    return caminho


def linha(data, poco, oleo=480.0, horas=24.0, flow="production", whp=60.0):
    return {
        "DATEPRD": data,
        "NPD_WELL_BORE_NAME": poco,
        "ON_STREAM_HRS": horas,
        "AVG_WHP_P": whp,
        "AVG_WHT_P": 70.0,
        "AVG_CHOKE_SIZE_P": 55.0,
        "BORE_OIL_VOL": oleo,
        "FLOW_KIND": flow,
    }


def test_converte_para_formato_da_api(tmp_path):
    df = carregar_producao(escrever(tmp_path, [linha("01-Jan-2014", "15/9-F-12", oleo=480.0, horas=12.0)]))
    r = df.iloc[0]
    assert r["poco_id"] == "15/9-F-12"
    assert r["caudal_oleo_m3h"] == 40.0  # 480 m³ em 12 h
    assert r["fonte"] == "volve"
    assert str(r["timestamp"].tz) == "UTC"


def test_filtra_linhas_invalidas(tmp_path):
    linhas = [
        linha("01-Jan-2014", "A"),
        linha("01-Jan-2014", "B", horas=0),  # poço parado
        linha("01-Jan-2014", "C", oleo=0),  # sem produção
        linha("01-Jan-2014", "D", flow="injection"),  # injetor
        linha("01-Jan-2014", "E", whp=None),  # sem pressão
    ]
    assert carregar_producao(escrever(tmp_path, linhas))["poco_id"].tolist() == ["A"]


def test_replay_agrupa_por_dia_pela_ordem(tmp_path):
    linhas = [linha("02-Jan-2014", "A"), linha("01-Jan-2014", "A"), linha("01-Jan-2014", "B")]
    dias = list(dias_de_producao(carregar_producao(escrever(tmp_path, linhas))))
    assert [len(d) for d in dias] == [2, 1]
    assert dias[0][0]["timestamp"].startswith("2014-01-01")


def test_le_excel_na_folha_diaria(tmp_path):
    df = carregar_producao(escrever(tmp_path, [linha("01-Jan-2014", "A")], nome="volve.xlsx"))
    assert len(df) == 1


def test_erros_claros(tmp_path):
    with pytest.raises(ErroVolve, match="não encontrado"):
        carregar_producao(tmp_path / "nao-existe.csv")
    caminho = tmp_path / "mau.csv"
    pd.DataFrame({"DATEPRD": ["01-Jan-2014"]}).to_csv(caminho, index=False)
    with pytest.raises(ErroVolve, match="Colunas em falta"):
        carregar_producao(caminho)
