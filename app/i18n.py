"""Textos do dashboard em inglês e português.

O idioma escolhe-se com a variável IDIOMA no .env ("en" por defeito, ou "pt").
A API e a base de dados continuam em português (OK, ATENÇÃO, CRÍTICO...);
aqui só se traduz o que a pessoa vê no ecrã.
"""
from __future__ import annotations

import os

IDIOMAS = ("en", "pt")

TEXTOS: dict[str, dict[str, str]] = {
    "en": {
        "lang_html": "en",
        "titulo_pagina_monitor": "Offshore Digital Twin",
        "titulo_pagina_consola": "Control Console",
        "erro_api": "Could not connect to the API at {url}: {erro}",
        "titulo_volve": "Volve field — replay of real production data",
        "legenda_volve": (
            "Production data from the Volve field (Equinor and partners), under the Equinor Open Data Licence. "
            "Non-commercial use. Shows the same architecture designed for operations such as Blocks 17 and 32."
        ),
        "titulo_simulacao": "Offshore telemetry — wells inspired by Blocks 17 and 32",
        "legenda_simulacao": "Simulated data from a simplified physical model. Contains no real data from any operator.",
        "aviso_consola": "CONTROL CONSOLE — access restricted to the control room's local network.",
        "aviso_monitor": "Read-only monitoring. Actuation commands only exist in the control room console.",
        "filtros": "Filters",
        "poco": "Well",
        "todos": "ALL",
        "leituras": "Readings to show",
        "limites": "Limits: warning > {atencao:.0f} bar · critical > {critico:.0f} bar",
        "preco": "Reference price: {preco:.0f} USD/barrel",
        "modelo": "Anomaly model",
        "treinado": "Trained",
        "nao_treinado": "Not trained yet",
        "retreinar": "Retrain with database data",
        "resultado_treino": "{amostras} samples · {anomalias} anomalies ({taxa}%)",
        "serie_critico": "Critical",
        "serie_anomalia": "Anomaly (ML)",
        "linha_critico": "Critical {v:.0f} bar",
        "linha_atencao": "Warning {v:.0f} bar",
        "comando_enviado": "Command {acao} sent to {poco}. Waiting for execution in the field.",
        "comando_falhou": "Failed to send command: {erro}",
        "erro_leitura": "Error reading the API: {erro}",
        "a_aguardar": "Waiting for telemetry from the field...",
        "alerta_critico": "CRITICAL ALERT — {poco}: {p:.1f} bar (limit {lim:.0f} bar)",
        "alerta_atencao": "Warning — {poco}: {p:.1f} bar",
        "atuacao": "Well actuation",
        "ultimo_comando": "Last command: {acao} · {estado}",
        "sem_comandos": "No commands sent",
        "btn_aliviar": "Relieve pressure",
        "btn_repor": "Reset to normal",
        "kpi_pressao": "Average pressure",
        "kpi_temperatura": "Average temperature",
        "kpi_caudal": "Oil flow rate",
        "kpi_barris": "{v:,.0f} barrels/day",
        "kpi_receita": "Estimated revenue",
        "kpi_risco": "Production at risk",
        "kpi_paragem": "possible shutdown",
        "kpi_sem_risco": "no risk",
        "tab_leituras": "Recent readings",
        "tab_comandos": "Command log",
        "erro_comandos": "Error reading commands: {erro}",
    },
    "pt": {
        "lang_html": "pt-PT",
        "titulo_pagina_monitor": "Digital Twin Offshore",
        "titulo_pagina_consola": "Consola de Controlo",
        "erro_api": "Não foi possível ligar à API em {url}: {erro}",
        "titulo_volve": "Campo Volve — replay de dados reais de produção",
        "legenda_volve": (
            "Dados de produção do campo Volve (Equinor e parceiros), sob a Equinor Open Data Licence. "
            "Uso não comercial. Mostra a mesma arquitetura desenhada para operações como os Blocos 17 e 32."
        ),
        "titulo_simulacao": "Telemetria offshore — poços inspirados nos Blocos 17 e 32",
        "legenda_simulacao": "Dados simulados com um modelo físico simplificado. Não contém dados reais de nenhuma operadora.",
        "aviso_consola": "CONSOLA DE CONTROLO — acesso restrito à rede local da sala de controlo.",
        "aviso_monitor": "Monitorização só de leitura. Os comandos de atuação só existem na consola da sala de controlo.",
        "filtros": "Filtros",
        "poco": "Poço",
        "todos": "TODOS",
        "leituras": "Leituras a mostrar",
        "limites": "Limites: atenção > {atencao:.0f} bar · crítico > {critico:.0f} bar",
        "preco": "Preço de referência: {preco:.0f} USD/barril",
        "modelo": "Modelo de anomalias",
        "treinado": "Treinado",
        "nao_treinado": "Ainda não treinado",
        "retreinar": "Retreinar com os dados da BD",
        "resultado_treino": "{amostras} amostras · {anomalias} anomalias ({taxa}%)",
        "serie_critico": "Crítico",
        "serie_anomalia": "Anomalia (ML)",
        "linha_critico": "Crítico {v:.0f} bar",
        "linha_atencao": "Atenção {v:.0f} bar",
        "comando_enviado": "Comando {acao} enviado para {poco}. Aguarda execução no campo.",
        "comando_falhou": "Falha ao enviar comando: {erro}",
        "erro_leitura": "Erro ao ler a API: {erro}",
        "a_aguardar": "A aguardar telemetria do campo...",
        "alerta_critico": "ALERTA CRÍTICO — {poco}: {p:.1f} bar (limite {lim:.0f} bar)",
        "alerta_atencao": "Atenção — {poco}: {p:.1f} bar",
        "atuacao": "Atuação nos poços",
        "ultimo_comando": "Último comando: {acao} · {estado}",
        "sem_comandos": "Sem comandos enviados",
        "btn_aliviar": "Aliviar pressão",
        "btn_repor": "Repor normal",
        "kpi_pressao": "Pressão média",
        "kpi_temperatura": "Temperatura média",
        "kpi_caudal": "Caudal de petróleo",
        "kpi_barris": "{v:,.0f} barris/dia",
        "kpi_receita": "Receita estimada",
        "kpi_risco": "Produção em risco",
        "kpi_paragem": "paragem possível",
        "kpi_sem_risco": "sem risco",
        "tab_leituras": "Leituras recentes",
        "tab_comandos": "Registo de comandos",
        "erro_comandos": "Erro ao ler comandos: {erro}",
    },
}

# Valores que vêm da API (em português) e como aparecem no ecrã
VALORES: dict[str, dict[str, str]] = {
    "en": {
        "OK": "OK", "ATENÇÃO": "WARNING", "CRÍTICO": "CRITICAL",
        "PENDENTE": "PENDING", "EXECUTADO": "EXECUTED", "REJEITADO": "REJECTED",
        "ALIVIAR_PRESSAO": "RELIEVE_PRESSURE", "REPOR_NORMAL": "RESET_NORMAL",
        "simulacao": "simulation", "volve": "volve",
    },
    "pt": {},  # em português os valores aparecem como estão
}

COLUNAS: dict[str, dict[str, str]] = {
    "en": {
        "id": "id", "poco_id": "well", "timestamp": "timestamp (UTC)", "pressao_bar": "pressure (bar)",
        "temperatura_celsius": "temperature (°C)", "caudal_oleo_m3h": "oil flow (m³/h)",
        "abertura_choke_pct": "choke (%)", "status_seguranca": "safety status", "anomalia_ml": "ML anomaly",
        "fonte": "source", "acao": "action", "estado": "status", "operador": "operator",
        "criado_em": "created (UTC)", "executado_em": "executed (UTC)", "detalhe": "detail",
    },
    "pt": {
        "id": "id", "poco_id": "poço", "timestamp": "data/hora (UTC)", "pressao_bar": "pressão (bar)",
        "temperatura_celsius": "temperatura (°C)", "caudal_oleo_m3h": "caudal (m³/h)",
        "abertura_choke_pct": "choke (%)", "status_seguranca": "estado de segurança", "anomalia_ml": "anomalia ML",
        "fonte": "fonte", "acao": "ação", "estado": "estado", "operador": "operador",
        "criado_em": "criado (UTC)", "executado_em": "executado (UTC)", "detalhe": "detalhe",
    },
}


def idioma_atual() -> str:
    idioma = os.getenv("IDIOMA", "en").strip().lower()
    return idioma if idioma in IDIOMAS else "en"


def t(chave: str, idioma: str | None = None, **valores) -> str:
    texto = TEXTOS[idioma or idioma_atual()][chave]
    return texto.format(**valores) if valores else texto


def v(valor: str, idioma: str | None = None) -> str:
    """Traduz um valor vindo da API (estado, ação...)."""
    return VALORES[idioma or idioma_atual()].get(valor, valor)
