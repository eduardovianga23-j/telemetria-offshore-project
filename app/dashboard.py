"""Dashboard do Digital Twin (Streamlit).

O mesmo código corre em dois papéis, escolhidos por variável de ambiente:

- MONITORIZAÇÃO (CONTROLO_ATIVO=false, por defeito): só leitura. É a versão
  que pode ser publicada para engenheiros em terra, atrás de uma camada de
  acesso como o Cloudflare Access.
- CONSOLA DE CONTROLO (CONTROLO_ATIVO=true): mostra os comandos e o retreino
  do modelo. Representa a sala de controlo e fica só na rede local.

O idioma dos textos escolhe-se com IDIOMA ("en" por defeito, ou "pt").
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

try:  # a correr como pacote (testes)
    from app.i18n import COLUNAS, idioma_atual, t, v
    from app.series import com_quebras
except ImportError:  # a correr com "streamlit run app/dashboard.py"
    from i18n import COLUNAS, idioma_atual, t, v
    from series import com_quebras

BASE_API_URL = os.getenv("BASE_API_URL", "http://127.0.0.1:8000").rstrip("/")
CONTROLO_ATIVO = os.getenv("CONTROLO_ATIVO", "false").lower() == "true"
CHAVE_CONTROLO = os.getenv("API_KEY_CONTROLO", "")
M3_POR_BARRIL = 0.158987
IDIOMA = idioma_atual()
TODOS = "__todos__"  # valor interno do filtro "todos os poços"

st.set_page_config(
    page_title=t("titulo_pagina_consola") if CONTROLO_ATIVO else t("titulo_pagina_monitor"),
    page_icon="⚓",
    layout="wide",
)

# Impede o browser de traduzir a página automaticamente (o Chrome trocava
# "Pressão" por "Imprensa"). O componente corre num iframe da mesma origem e
# marca o documento principal com o idioma certo e "não traduzir".
# O HTML é fixo, escrito aqui, nunca vem de dados externos.
st.iframe(
    f"""<script>
    const doc = window.parent.document;
    doc.documentElement.setAttribute("lang", "{t('lang_html')}");
    doc.documentElement.setAttribute("translate", "no");
    doc.documentElement.classList.add("notranslate");
    if (!doc.querySelector('meta[name="google"]')) {{
        const m = doc.createElement("meta");
        m.name = "google"; m.content = "notranslate";
        doc.head.appendChild(m);
    }}
    </script>""",
    height=1,
)


# ----------------------------------------------------------------- acesso API
def api_get(caminho: str, **params):
    r = requests.get(f"{BASE_API_URL}{caminho}", params=params, timeout=5)
    r.raise_for_status()
    return r.json()


def api_post(caminho: str, json: dict | None = None):
    r = requests.post(
        f"{BASE_API_URL}{caminho}", json=json, headers={"X-API-Key": CHAVE_CONTROLO}, timeout=15
    )
    if r.status_code >= 400:
        detalhe = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise RuntimeError(f"{r.status_code}: {detalhe}")
    return r.json()


def tabela(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara uma tabela para o ecrã: valores e nomes de colunas no idioma escolhido."""
    df = df.copy()
    for col in ("status_seguranca", "acao", "estado", "fonte"):
        if col in df.columns:
            df[col] = df[col].map(lambda x: v(x) if isinstance(x, str) else x)
    return df.rename(columns=COLUNAS[IDIOMA])


try:
    info = api_get("/api/info")
except requests.RequestException as e:
    st.error(t("erro_api", url=BASE_API_URL, erro=e))
    st.stop()

MODO_VOLVE = info["modo_dados"] == "volve"
# Intervalo a partir do qual o gráfico parte a linha (Volve: dados diários)
LIMIAR_QUEBRA = pd.Timedelta(days=3) if MODO_VOLVE else pd.Timedelta(minutes=2)
LIM_ATENCAO = info["limite_atencao_bar"]
LIM_CRITICO = info["limite_critico_bar"]
PRECO_M3 = info["preco_barril_usd"] / M3_POR_BARRIL

# ---------------------------------------------------------------- cabeçalho
if MODO_VOLVE:
    st.title(t("titulo_volve"))
    st.caption(t("legenda_volve"))
else:
    st.title(t("titulo_simulacao"))
    st.caption(t("legenda_simulacao"))

if CONTROLO_ATIVO:
    st.warning(t("aviso_consola"), icon="🔒")
else:
    st.info(t("aviso_monitor"), icon="👁️")

# ------------------------------------------------------------------- filtros
st.sidebar.header(t("filtros"))
try:
    pocos = [p["poco_id"] for p in api_get("/api/pocos")]
except requests.RequestException:
    pocos = []
poco_sel = st.sidebar.selectbox(t("poco"), [TODOS, *pocos], format_func=lambda p: t("todos") if p == TODOS else p)
janela = st.sidebar.slider(t("leituras"), 50, 2000, 300, step=50)
st.sidebar.caption(t("limites", atencao=LIM_ATENCAO, critico=LIM_CRITICO))
st.sidebar.caption(t("preco", preco=info["preco_barril_usd"]))

if CONTROLO_ATIVO:
    st.sidebar.divider()
    st.sidebar.subheader(t("modelo"))
    st.sidebar.caption(t("treinado") if info["modelo_ml_treinado"] else t("nao_treinado"))
    if st.sidebar.button(t("retreinar"), width="stretch"):
        try:
            res = api_post("/api/ml/retreinar")
            st.sidebar.success(t("resultado_treino", amostras=res["total_amostras"],
                                 anomalias=res["anomalias_encontradas"], taxa=res["taxa_anomalias_pct"]))
        except Exception as e:
            st.sidebar.error(str(e))


# ------------------------------------------------------------ componentes
def grafico_pressao(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for poco, g in df.groupby("poco_id"):
        xs, ys = com_quebras(g, "pressao_bar", LIMIAR_QUEBRA)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=poco, connectgaps=False))
    crit = df[df["status_seguranca"] == "CRÍTICO"]
    if not crit.empty:
        fig.add_trace(
            go.Scatter(x=crit["timestamp"], y=crit["pressao_bar"], mode="markers", name=t("serie_critico"),
                       marker=dict(color="#d62728", size=9, symbol="x"))
        )
    anom = df[df["anomalia_ml"] == True]  # noqa: E712
    if not anom.empty:
        fig.add_trace(
            go.Scatter(x=anom["timestamp"], y=anom["pressao_bar"], mode="markers", name=t("serie_anomalia"),
                       marker=dict(color="#9467bd", size=11, symbol="circle-open", line=dict(width=2)))
        )
    fig.add_hline(y=LIM_CRITICO, line_dash="dash", line_color="#d62728", annotation_text=t("linha_critico", v=LIM_CRITICO))
    fig.add_hline(y=LIM_ATENCAO, line_dash="dot", line_color="#ff7f0e", annotation_text=t("linha_atencao", v=LIM_ATENCAO))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="bar", legend_title_text="")
    return fig


def grafico_simples(df: pd.DataFrame, coluna: str, unidade: str) -> go.Figure:
    fig = go.Figure()
    for poco, g in df.groupby("poco_id"):
        xs, ys = com_quebras(g, coluna, LIMIAR_QUEBRA)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=poco, connectgaps=False))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), yaxis_title=unidade, legend_title_text="")
    return fig


def usd_hora(valor: float) -> str:
    """Formato compacto para caber no indicador: 146955 -> "147k USD/h"."""
    return f"{valor / 1000:,.0f}k USD/h" if valor >= 10_000 else f"{valor:,.0f} USD/h"


def enviar_comando(poco: str, acao: str) -> None:
    try:
        api_post("/api/comando", {"poco_id": poco, "acao": acao, "operador": "consola-local"})
        st.toast(t("comando_enviado", acao=v(acao), poco=poco), icon="🛠️")
    except Exception as e:
        st.toast(t("comando_falhou", erro=e), icon="⚠️")


# ------------------------------------------------- atualização a cada 3 s
@st.fragment(run_every="3s")
def painel(poco: str, n: int) -> None:
    params = {"limit": n} if poco == TODOS else {"limit": n, "poco_id": poco}
    try:
        df = pd.DataFrame(api_get("/api/historico", **params))
        resumo = pd.DataFrame(api_get("/api/pocos"))
    except requests.RequestException as e:
        st.error(t("erro_leitura", erro=e))
        return
    if df.empty:
        st.warning(t("a_aguardar"))
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601")
    if poco != TODOS:
        resumo = resumo[resumo["poco_id"] == poco]

    # Alertas (iguais no monitor e na consola)
    for linha in resumo.itertuples():
        if linha.status_seguranca == "CRÍTICO":
            st.error(t("alerta_critico", poco=linha.poco_id, p=linha.pressao_bar, lim=LIM_CRITICO))
        elif linha.status_seguranca == "ATENÇÃO":
            st.warning(t("alerta_atencao", poco=linha.poco_id, p=linha.pressao_bar))

    # Painel de atuação: só na consola, sempre disponível, por poço.
    # Numa sala de controlo real o operador pode atuar a qualquer momento,
    # por exemplo de forma preventiva quando vê a pressão a subir.
    if CONTROLO_ATIVO and not MODO_VOLVE:
        with st.container(border=True):
            st.subheader(t("atuacao"))
            try:
                comandos = api_get("/api/comandos", limit=100)
            except requests.RequestException:
                comandos = []
            ultimo_por_poco: dict[str, dict] = {}
            for c in comandos:  # vêm do mais recente para o mais antigo
                ultimo_por_poco.setdefault(c["poco_id"], c)

            for linha in resumo.itertuples():
                c_nome, c_estado, c_cmd, c_b1, c_b2 = st.columns([1.2, 1.4, 2.4, 1.2, 1.2], vertical_alignment="center")
                c_nome.markdown(f"**{linha.poco_id}**")
                icone = {"CRÍTICO": "🔴", "ATENÇÃO": "🟠"}.get(linha.status_seguranca, "🟢")
                c_estado.write(f"{icone} {linha.pressao_bar:.1f} bar")
                ultimo = ultimo_por_poco.get(linha.poco_id)
                c_cmd.caption(
                    t("ultimo_comando", acao=v(ultimo["acao"]), estado=v(ultimo["estado"])) if ultimo else t("sem_comandos")
                )
                tipo = "primary" if linha.status_seguranca == "CRÍTICO" else "secondary"
                if c_b1.button(t("btn_aliviar"), key=f"alivio-{linha.poco_id}", type=tipo, width="stretch"):
                    enviar_comando(linha.poco_id, "ALIVIAR_PRESSAO")
                if c_b2.button(t("btn_repor"), key=f"repor-{linha.poco_id}", width="stretch"):
                    enviar_comando(linha.poco_id, "REPOR_NORMAL")

    # Indicadores da última leitura de cada poço visível
    ultimas = df.sort_values("timestamp").groupby("poco_id").tail(1)
    caudal_total = ultimas["caudal_oleo_m3h"].sum()
    receita_h = caudal_total * PRECO_M3
    em_risco = ultimas.loc[ultimas["status_seguranca"] == "CRÍTICO", "caudal_oleo_m3h"].sum() * PRECO_M3

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(t("kpi_pressao"), f"{ultimas['pressao_bar'].mean():.1f} bar")
    k2.metric(t("kpi_temperatura"), f"{ultimas['temperatura_celsius'].mean():.1f} °C")
    k3.metric(t("kpi_caudal"), f"{caudal_total:.0f} m³/h", t("kpi_barris", v=caudal_total * 24 / M3_POR_BARRIL),
              delta_color="off")
    k4.metric(t("kpi_receita"), usd_hora(receita_h))
    k5.metric(t("kpi_risco"), usd_hora(em_risco),
              t("kpi_paragem") if em_risco else t("kpi_sem_risco"), delta_color="inverse" if em_risco else "off")

    st.plotly_chart(grafico_pressao(df), width="stretch")
    c1, c2 = st.columns(2)
    c1.plotly_chart(grafico_simples(df, "caudal_oleo_m3h", "m³/h"), width="stretch")
    c2.plotly_chart(grafico_simples(df, "temperatura_celsius", "°C"), width="stretch")

    t1, t2 = st.tabs([t("tab_leituras"), t("tab_comandos")])
    with t1:
        st.dataframe(tabela(df.sort_values("timestamp", ascending=False).head(30)), width="stretch", hide_index=True)
    with t2:
        try:
            st.dataframe(tabela(pd.DataFrame(api_get("/api/comandos", limit=30))), width="stretch", hide_index=True)
        except requests.RequestException as e:
            st.error(t("erro_comandos", erro=e))


painel(poco_sel, janela)
