import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração inicial do layout da página
st.set_page_config(page_title="Digital Twin - Telemetria Offshore", page_icon="⚓", layout="wide")
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# Configuração da URL da API suportando variáveis de ambiente (Crucial para Docker)
BASE_API_URL = os.getenv("BASE_API_URL", "http://127.0.0.1:8000")
API_HISTORICO_URL = f"{BASE_API_URL}/api/historico"
API_ML_RETRAIN_URL = f"{BASE_API_URL}/api/ml/retreinar"
API_COMANDO_URL = f"{BASE_API_URL}/api/comando"

LIMITE_CRITICO = 150.0
PRECO_M3_OLEO = 450.0  # Preço estimado por m³ de petróleo (~ $70-75/barril)

# ==============================================================================
# ⚙️ SIDEBAR (Executada fora do fragmento)
# ==============================================================================
st.sidebar.header("⚙️ Configurações & Filtros")

# 🤖 Retreinamento MLOps
st.sidebar.subheader("🤖 Modelo de IA (Isolation Forest)")
if st.sidebar.button("🔄 Retreinar Modelo com BD", use_container_width=True):
    with st.sidebar.status("A treinar modelo no servidor...", expanded=True) as status_box:
        try:
            res = requests.post(API_ML_RETRAIN_URL, timeout=10)
            if res.status_code == 200:
                dados_ml = res.json()
                status_box.update(label="✅ Modelo Atualizado!", state="complete")
                st.sidebar.success("Treino concluído e guardado em disco!")
                st.sidebar.metric("Amostras Treinadas", dados_ml.get("total_amostras", 0))
                st.sidebar.metric(
                    "Anomalias Detetadas", 
                    f"{dados_ml.get('anomalias_encontradas', 0)} ({dados_ml.get('taxa_anomalias_pct', 0)}%)"
                )
            else:
                erro_msg = res.json().get("detail", "Erro desconhecido ao retreinar.")
                status_box.update(label="❌ Falha no Treino", state="error")
                st.sidebar.error(erro_msg)
        except Exception as e:
            status_box.update(label="❌ Erro de Conexão", state="error")
            st.sidebar.error(f"Erro ao ligar à API: {e}")

st.sidebar.divider()

# 🎯 Filtros Estáticos
st.sidebar.subheader("🎯 Filtros de Visualização")

poco_selecionado = st.sidebar.selectbox(
    "Selecionar Poço:", 
    ["TODOS", "Poco_Bloco17_A", "Poco_Bloco17_B", "Poco_Bloco32_C"], 
    key="sb_poco"
)

filtro_status = st.sidebar.multiselect(
    "Filtrar por Status de Segurança:",
    options=["OK", "ATENÇÃO", "CRÍTICO"],
    default=["OK", "ATENÇÃO", "CRÍTICO"],
    key="ms_status"
)


# ==============================================================================
# ⚓ TÍTULO DA PÁGINA
# ==============================================================================
st.title("⚓ Sala de Controle e Telemetria - Bloco 17 e 32")
st.caption("Monitorização em tempo real com atuação remota, IA e impacto financeiro.")


# ==============================================================================
# 🔄 FRAGMENTO (Renderização e atualização contínua)
# ==============================================================================
@st.fragment(run_every="3s")
def render_dashboard(poco_sel, status_sel):
    try:
        response = requests.get(API_HISTORICO_URL, timeout=5)
        if response.status_code != 200:
            st.error(f"Erro na API (Status {response.status_code}).")
            return
        data = response.json()
    except Exception as e:
        st.error(f"Não foi possível ligar à API em '{BASE_API_URL}': {e}")
        return

    df = pd.DataFrame(data)

    if df.empty:
        st.warning("Aguardando dados da telemetria...")
        return

    if "timestamp" in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values(by="timestamp", ascending=True)

    # Aplica os filtros passados por argumento
    df_filtrado = df.copy()
    if poco_sel != "TODOS":
        df_filtrado = df_filtrado[df_filtrado["poco_id"] == poco_sel]

    if "status_seguranca" in df_filtrado.columns and status_sel:
        df_filtrado = df_filtrado[df_filtrado["status_seguranca"].isin(status_sel)]

    # 🚨 BANNERS E BOTÃO DE ALÍVIO DE PRESSÃO (SISTEMA DE SAFETY/FLARE)
    ultima_leitura = df_filtrado.iloc[-1] if not df_filtrado.empty else None

    if ultima_leitura is not None:
        pressao_val = ultima_leitura["pressao_bar"]
        poco_val = ultima_leitura["poco_id"]
        status_seg = ultima_leitura.get("status_seguranca", "OK")

        if pressao_val > LIMITE_CRITICO or status_seg == "CRÍTICO":
            c_msg, c_btn = st.columns([3, 1])
            with c_msg:
                st.error(
                    f"🚨 **ALERTA CRÍTICO DE PRESSÃO!** Poço **{poco_val}** registou **{pressao_val:.2f} bar** "
                    f"(Status: {status_seg}). Ação imediata recomendada!"
                )
            with c_btn:
                if st.button("🔧 Aliviar Pressão", key="btn_alivio", type="primary", use_container_width=True):
                    try:
                        res = requests.post(
                            API_COMANDO_URL, 
                            json={"poco_id": poco_val, "acao": "ALIVIAR_PRESSAO"},
                            timeout=5
                        )
                        if res.status_code == 200:
                            st.toast(f"✅ Comando de alívio enviado para {poco_val}!", icon="🛠️")
                        else:
                            st.toast("❌ Falha ao enviar comando de alívio.", icon="⚠️")
                    except Exception as err:
                        st.toast(f"Erro de conexão: {err}", icon="❌")
        else:
            st.success(
                f"✅ **[SISTEMA NORMAL]** Última leitura do poço **{poco_val}**: **{pressao_val:.2f} bar** | Status: **{status_seg}**"
            )

    # 📊 KPIs PRINCIPAIS E IMPACTO FINANCEIRO
    col1, col2, col3, col4, col5 = st.columns(5)

    if ultima_leitura is not None:
        leitura_anterior = df_filtrado.iloc[-2] if len(df_filtrado) > 1 else None

        col1.metric("Poço Visualizado", poco_sel)

        pressao_atual = ultima_leitura["pressao_bar"]
        delta_p = f"{pressao_atual - leitura_anterior['pressao_bar']:.2f} bar" if leitura_anterior is not None else None
        col2.metric("Pressão Atual", f"{pressao_atual:.2f} bar", delta=delta_p)

        temp_atual = ultima_leitura["temperatura_celsius"]
        delta_t = f"{temp_atual - leitura_anterior['temperatura_celsius']:.2f} °C" if leitura_anterior is not None else None
        col3.metric("Temperatura", f"{temp_atual:.2f} °C", delta=delta_t)

        vazao_atual = float(ultima_leitura.get('vazao_m3h', 400.0) or 400.0)
        col4.metric("Vazão de Óleo", f"{vazao_atual:.2f} m³/h")

        # 💶 KPI FINANCEIRO (Custo do Flare vs Receita Teórica)
        if status_seg == "CRÍTICO":
            # Perda estimada em queima de gás/desvio de emergência (15% da vazão direcionada ao flare)
            custo_flare_hora = vazao_atual * PRECO_M3_OLEO * 0.15
            col5.metric(
                "Risco Financ. (Flare)", 
                f"€ {custo_flare_hora:,.2f} /h", 
                delta="PERDA ELEVADA", 
                delta_color="inverse"
            )
        else:
            valor_producao_hora = vazao_atual * PRECO_M3_OLEO
            col5.metric("Receita Est. Produção", f"€ {valor_producao_hora:,.2f} /h")

    st.divider()

    # 📈 GRÁFICOS
    c1, c2 = st.columns(2)

    with c1:
        st.subheader(f"📈 Pressão & Detecção - {poco_sel}")
        fig_p = px.line(
            df_filtrado, 
            x="timestamp", 
            y="pressao_bar", 
            color="poco_id", 
            markers=True,
            title="Pressão em Tempo Real"
        )
        fig_p.add_hline(y=LIMITE_CRITICO, line_dash="dash", line_color="red", annotation_text="Limite Crítico (150 bar)")
        
        if "status_seguranca" in df_filtrado.columns:
            criticos_df = df_filtrado[df_filtrado["status_seguranca"] == "CRÍTICO"]
            if not criticos_df.empty:
                fig_p.add_trace(
                    go.Scatter(
                        x=criticos_df["timestamp"],
                        y=criticos_df["pressao_bar"],
                        mode="markers",
                        marker=dict(color="red", size=10, symbol="x"),
                        name="Ponto Crítico"
                    )
                )

        st.plotly_chart(fig_p, use_container_width=True)

    with c2:
        st.subheader(f"🌡️ Histórico de Temperatura - {poco_sel}")
        fig_t = px.line(
            df_filtrado, 
            x="timestamp", 
            y="temperatura_celsius", 
            color="poco_id", 
            markers=True,
            title="Temperatura em Tempo Real"
        )
        st.plotly_chart(fig_t, use_container_width=True)

    # 📋 TABELA DE TELEMETRIA RECENTE
    st.subheader("📋 Tabela de Leituras Recentes")
    st.dataframe(
        df_filtrado.sort_values(by="timestamp", ascending=False).head(20), 
        use_container_width=True,
        hide_index=True
    )

# Executa o fragmento com os filtros da sidebar
render_dashboard(poco_selecionado, filtro_status)