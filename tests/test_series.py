import pandas as pd

from app.series import com_quebras


def test_parte_a_linha_em_intervalos_grandes():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2008-01-01", "2008-01-02", "2016-01-01", "2016-01-02"], utc=True),
        "pressao_bar": [100, 99, 30, 31],
    })
    xs, ys = com_quebras(df, "pressao_bar", pd.Timedelta(days=30))
    assert ys == [100, 99, None, 30, 31]
    assert xs[2] is None


def test_sem_intervalos_nao_altera():
    df = pd.DataFrame({"timestamp": pd.to_datetime(["2008-01-02", "2008-01-01"], utc=True), "pressao_bar": [2, 1]})
    assert com_quebras(df, "pressao_bar", pd.Timedelta(days=30))[1] == [1, 2]
