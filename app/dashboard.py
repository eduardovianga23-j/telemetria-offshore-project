"""Dashboard do Digital Twin (Streamlit).

O mesmo código corre em dois papéis, escolhidos por variável de ambiente:

- MONITORIZAÇÃO (CONTROLO_ATIVO=false, por defeito): só leitura. É a versão
  que pode ser publicada para engenheiros em terra, atrás de uma camada de
  acesso como o Cloudflare Access.
- CONSOLA DE CONTROLO (CONTROLO_ATIVO=true): mostra os comandos e o retreino
  do modelo. Representa a sala de controlo e fica só na rede local.
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

BASE_API_URL = os.getenv("BASE_API_URL", "http://127.0.0.1:8000").rstrip("/")
CONTROLO_ATIVO = os.getenv("CONTROLO_ATIVO", "false").lower() == "true"
CHAVE_CONTROLO = os.getenv("API_KEY_CONTROLO", "")
M3_POR_BARRIL = 0.158987

st.set_page_config(
    page_title="Consola de Controlo" if CONTROLO_ATIVO else "Digital Twin Offshore",
    page_icon="⚓",
    layout="wide",
)

# Impede o browser de traduzir a página automaticamente (o Chrome trocava
# "Pressão" por "Imprensa"). O componente corre num iframe da mesma origem e
# marca o documento principal como português e "não traduzir".
# O HTML é fixo, escrito aqui, nunca vem de dados externos.
st.iframe(
    """<script>
    const doc = window.parent.document;
    doc.documentElement.setAttribute("lang", "pt-PT");
    doc.documentElement.setAttribute("translate", "no");
    doc.documentElement.classList.add("notranslate");
    if (!doc.querySelector('meta[name="google"]')) {
        const m = doc.createElement("meta");
        m.name = "google"; m.content = "notranslate";
        doc.head.appendChild(m);
    }
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


try:
    info = api_get("/api/info")
except requests.RequestException as e:
    st.error(f"Não foi possível ligar à API em {BASE_API_URL}: {e}")
    st.stop()

MODO_VOLVE = info["modo_dados"] == "volve"
LIM_ATENCAO = info["limite_atencao_bar"]
LIM_CRITICO = info["limite_critico_bar"]
PRECO_M3 = info["preco_barril_usd"] / M3_POR_BARRIL

# ---------------------------------------------------------------- cabeçalho
if MODO_VOLVE:
    st.title("Campo Volve — replay de dados reais de produção")
    st.caption(
        "Dados de produção do campo Volve (Equinor e parceiros), sob a Equinor Open Data Licence. "
        "Uso não comercial. Mostra a mesma arquitetura desenhada para operações como os Blocos 17 e 32."
    )
else:
    st.title("Telemetria offshore — poços inspirados nos Blocos 17 e 32")
    st.caption(
        "Dados simulados com um modelo físico simplificado. Não contém dados reais de nenhuma operadora."
    )

if CONTROLO_ATIVO:
    st.warning("CONSOLA DE CONTROLO — acesso restrito à rede local da sala de controlo.", icon="🔒")
else:
    st.info(
        "Monitorização só de leitura. Os comandos de atuação só existem na consola da sala de controlo.",
        icon="👁️",
    )

# ------------------------------------------------------------------- filtros
st.sidebar.header("Filtros")
try:
    pocos = [p["poco_id"] for p in api_get("/api/pocos")]
except requests.RequestException:
    pocos = []
poco_sel = st.sidebar.selectbox("Poço", ["TODOS", *pocos])
janela = st.sidebar.slider("Leituras a mostrar", 50, 2000, 300, step=50)
st.sidebar.caption(f"Limites: atenção > {LIM_ATENCAO:.0f} bar · crítico > {LIM_CRITICO:.0f} bar")
st.sidebar.caption(f"Preço de referência: {info['preco_barril_usd']:.0f} USD/barril")

if CONTROLO_ATIVO:
    st.sidebar.divider()
    st.sidebar.subheader("Modelo de anomalias")
    st.sidebar.caption("Treinado" if info["modelo_ml_treinado"] else "Ainda não treinado")
    if st.sidebar.button("Retreinar com os dados da BD", width="stretch"):
        try:
            res = api_post("/api/ml/retreinar")
            st.sidebar.success(
                f"{res['total_amostras']} amostras · {res['anomalias_encontradas']} anomalias "
                f"({res['taxa_anomalias_pct']}%)"
            )
        except Exception as e:
            st.sidebar.error(str(e))


# ------------------------------------------------------------ componentes
def grafico_pressao(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for poco, g in df.groupby("poco_id"):
        fig.add_trace(go.Scatter(x=g["timestamp"], y=g["pressao_bar"], mode="lines", name=poco))
    crit = df[df["status_seguranca"] == "CRÍTICO"]
    if not crit.empty:
        fig.add_trace(
            go.Scatter(x=crit["timestamp"], y=crit["pressao_bar"], mode="markers", name="Crítico",
                       marker=dict(color="#d62728", size=9, symbol="x"))
        )
    anom = df[df["anomalia_ml"] == True]  # noqa: E712
    if not anom.empty:
        fig.add_trace(
            go.Scatter(x=anom["timestamp"], y=anom["pressao_bar"], mode="markers", name="Anomalia (ML)",
                       marker=dict(color="#9467bd", size=11, symbol="circle-open", line=dict(width=2)))
        )
    fig.add_hline(y=LIM_CRITICO, line_dash="dash", line_color="#d62728", annotation_text=f"Crítico {LIM_CRITICO:.0f} bar")
    fig.add_hline(y=LIM_ATENCAO, line_dash="dot", line_color="#ff7f0e", annotation_text=f"Atenção {LIM_ATENCAO:.0f} bar")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="bar", legend_title_text="")
    return fig


def grafico_simples(df: pd.DataFrame, coluna: str, unidade: str) -> go.Figure:
    fig = go.Figure()
    for poco, g in df.groupby("poco_id"):
        fig.add_trace(go.Scatter(x=g["timestamp"], y=g[coluna], mode="lines", name=poco))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), yaxis_title=unidade, legend_title_text="")
    return fig


def enviar_comando(poco: str, acao: str) -> None:
    try:
        api_post("/api/comando", {"poco_id": poco, "acao": acao, "operador": "consola-local"})
        st.toast(f"Comando {acao} enviado para {poco}. Aguarda execução no campo.", icon="🛠️")
    except Exception as e:
        st.toast(f"Falha ao enviar comando: {e}", icon="⚠️")


# ------------------------------------------------- atualização a cada 3 s
@st.fragment(run_every="3s")
def painel(poco: str, n: int) -> None:
    params = {"limit": n} if poco == "TODOS" else {"limit": n, "poco_id": poco}
    try:
        df = pd.DataFrame(api_get("/api/historico", **params))
        resumo = pd.DataFrame(api_get("/api/pocos"))
    except requests.RequestException as e:
        st.error(f"Erro ao ler a API: {e}")
        return
    if df.empty:
        st.warning("A aguardar telemetria do campo...")
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601")
    if poco != "TODOS":
        resumo = resumo[resumo["poco_id"] == poco]

    # Alertas (iguais no monitor e na consola)
    for linha in resumo.itertuples():
        if linha.status_seguranca == "CRÍTICO":
            st.error(f"ALERTA CRÍTICO — {linha.poco_id}: {linha.pressao_bar:.1f} bar (limite {LIM_CRITICO:.0f} bar)")
        elif linha.status_seguranca == "ATENÇÃO":
            st.warning(f"Atenção — {linha.poco_id}: {linha.pressao_bar:.1f} bar")

    # Painel de atuação: só na consola, sempre disponível, por poço.
    # Numa sala de controlo real o operador pode atuar a qualquer momento,
    # por exemplo de forma preventiva quando vê a pressão a subir.
    if CONTROLO_ATIVO and not MODO_VOLVE:
        with st.container(border=True):
            st.subheader("Atuação nos poços")
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
                    f"Último comando: {ultimo['acao']} · {ultimo['estado']}" if ultimo else "Sem comandos enviados"
                )
                tipo = "primary" if linha.status_seguranca == "CRÍTICO" else "secondary"
                if c_b1.button("Aliviar pressão", key=f"alivio-{linha.poco_id}", type=tipo, width="stretch"):
                    enviar_comando(linha.poco_id, "ALIVIAR_PRESSAO")
                if c_b2.button("Repor normal", key=f"repor-{linha.poco_id}", width="stretch"):
                    enviar_comando(linha.poco_id, "REPOR_NORMAL")

    # Indicadores da última leitura de cada poço visível
    ultimas = df.sort_values("timestamp").groupby("poco_id").tail(1)
    caudal_total = ultimas["caudal_oleo_m3h"].sum()
    receita_h = caudal_total * PRECO_M3
    em_risco = ultimas.loc[ultimas["status_seguranca"] == "CRÍTICO", "caudal_oleo_m3h"].sum() * PRECO_M3

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Pressão média", f"{ultimas['pressao_bar'].mean():.1f} bar")
    k2.metric("Temperatura média", f"{ultimas['temperatura_celsius'].mean():.1f} °C")
    k3.metric("Caudal de petróleo", f"{caudal_total:.0f} m³/h", f"{caudal_total * 24 / M3_POR_BARRIL:,.0f} barris/dia",
              delta_color="off")
    k4.metric("Receita estimada", f"{receita_h:,.0f} USD/h")
    k5.metric("Produção em risco", f"{em_risco:,.0f} USD/h",
              "paragem possível" if em_risco else "sem risco", delta_color="inverse" if em_risco else "off")

    st.plotly_chart(grafico_pressao(df), width="stretch")
    c1, c2 = st.columns(2)
    c1.plotly_chart(grafico_simples(df, "caudal_oleo_m3h", "m³/h"), width="stretch")
    c2.plotly_chart(grafico_simples(df, "temperatura_celsius", "°C"), width="stretch")

    t1, t2 = st.tabs(["Leituras recentes", "Registo de comandos"])
    with t1:
        st.dataframe(df.sort_values("timestamp", ascending=False).head(30), width="stretch", hide_index=True)
    with t2:
        try:
            st.dataframe(pd.DataFrame(api_get("/api/comandos", limit=30)), width="stretch", hide_index=True)
        except requests.RequestException as e:
            st.error(f"Erro ao ler comandos: {e}")


painel(poco_sel, janela)
