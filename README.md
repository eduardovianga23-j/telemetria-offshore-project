# ⚓ Digital Twin & Telemetria Offshore — Bloco 17 & 32

Sistema de monitorização em tempo real, análise de risco visual e atuação remota para poços de petróleo offshore. O projeto simula a operação de um **Gêmeo Digital (Digital Twin)**, unindo geração contínua de telemetria, API REST de controlo, interface analítica interativa e cálculos de impacto financeiro em tempo real.

---

## 🎯 Objetivo e Contexto da Indústria

Em operações petrolíferas offshore (em alto-mar), a pressão na cabeça do poço (*wellhead pressure*) é uma das variáveis mais críticas para a integridade operacional. Uma sobrepressão não detetada pode causar acidentes graves, danos aos equipamentos submarinos, paragens não programadas da produção ou a necessidade de queima de gás de emergência (*flaring*), gerando elevadas perdas financeiras e ambientais.

**O objetivo deste projeto é demonstrar como uma arquitetura moderna de software resolve esse desafio ao:**
1. **Visualizar a saúde física do poço em tempo real** através de um Dashboard de Digital Twin.
2. **Alertar automaticamente** sobre anomalias de pressão acima do limite de segurança (150 bar).
3. **Permitir a atuação remota imediata (Alívio de Pressão)** para reverter estados de emergência diretamente a partir da sala de controlo.
4. **Calcular o impacto financeiro contínuo** de perdas operacionais associadas ao risco.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem Principal:** Python 3.10+
* **Backend / API REST:** FastAPI & Uvicorn (alta performance e validação de dados com Pydantic)
* **Frontend & Dashboard:** Streamlit (interface interativa) & Plotly (gráficos dinâmicos com zonas de risco)
* **Manipulação de Dados:** Pandas & Requests
* **DevOps & Containerização:** Docker & Docker Compose

---

## 🗂️ Estrutura e Explicação de Cada Ficheiro

| Ficheiro / Pasta | Função e Descrição Detalhada |
| :--- | :--- |
| **`app/main.py`** | **API REST (FastAPI):** Atua como o servidor central. Contém os endpoints para receber os dados de telemetria enviados pelo simulador, consultar o histórico armazenado de cada poço e processar o comando remoto de alívio de pressão. |
| **`app/simulator.py`** | **Serviço de Telemetria (Python):** Roda em segundo plano simulando sensores de campo (*sensors feed*). Gera continuamente leituras estocásticas de Pressão (bar), Temperatura (°C) e Vazão (m³/d) para os poços `POCO-01`, `POCO-02` e `POCO-03` e envia-as via `POST` para a API. |
| **`app/dashboard.py`** | **Interface de Operação (Streamlit + Plotly):** É o painel visual do operador offshore. Lê os dados da API a cada poucos segundos, calcula indicadores dinâmicos, desenha gráficos com pontos críticos e fornece os controlos de atuação remota. |
| **`docker-compose.yml`** | **Orquestrador de Containers:** Define e conecta os 3 serviços (`api`, `simulator` e `dashboard`), criando uma rede interna isolada para que comuniquem entre si automaticamente sem necessidade de configuração manual. |
| **`Dockerfile`** | **Receita de Build:** Define a imagem base do Python, copia o código-fonte para dentro do container e instala todas as bibliotecas necessárias. |
| **`requirements.txt`** | **Ficheiro de Dependências:** Lista todas as bibliotecas Python necessárias para que o projeto rode (`fastapi`, `uvicorn`, `streamlit`, `plotly`, `pandas`, `requests`). |
| **`README.md`** | Documentação técnica completa e detalhada do projeto. |

---

## 💾 Gestão da Base de Dados: Onde e Como são Guardados os Dados?

### Os dados estão no GitHub?
**Não.** Os dados não são estáticos nem estão guardados num ficheiro fixo no GitHub. Eles são **gerados dinamicamente em tempo real** assim que o sistema entra em funcionamento.

### Como funciona o armazenamento?
Para garantir respostas extremamente rápidas (latência próxima de zero), a API (`main.py`) utiliza um **armazenamento em memória RAM (*In-Memory Database / Buffer List*)**:
1. Quando a API inicia, ela cria uma estrutura de dados na memória do container.
2. Cada leitura enviada pelo simulador é adicionada a esta lista em memória.
3. Para evitar consumo ilimitado de memória, a API mantém automaticamente um histórico das leituras mais recentes necessárias para alimentar o Dashboard.
4. **Vantagem arquitetural:** Simula o comportamento de bases de dados de Séries Temporais (*Time-Series Databases* como InfluxDB ou TimescaleDB) utilizadas na indústria para telemetria IoT de alta frequência.

---

## 🖥️ Explicação do Dashboard & Lógica do Botão "Aliviar Pressão"

### 1. Visualização e Regras de Negócio
O Dashboard analisa a pressão do poço selecionado em tempo real e aplica as seguintes regras de segurança da engenharia offshore:
* 🟢 **NORMAL (Pressão < 130 bar):** Operação segura. Indicadores e cartões exibidos em verde.
* 🟡 **ATENÇÃO (130 bar ≤ Pressão ≤ 150 bar):** Poço em pré-sobrepressão.
* 🔴 **CRÍTICO (Pressão > 150 bar):** Alerta vermelho ativado! Risco de paragem iminente e início do cálculo financeiro de perda por queima de gás (*flare*).

### 2. O Gráfico Dinâmico
Construído com **Plotly**, exibe a curva temporal da pressão com:
* Uma **linha limite fixa vermelha em 150 bar**.
* **Marcadores vermelhos destacados** exatamente nos pontos em que a pressão ultrapassou a zona de segurança.

### 3. O Botão "Aliviar Pressão": Lógica, Porquê e Utilidade
* **Porquê existe?** Na vida real, ao identificar uma sobrepressão perigosa no painel, o engenheiro de operações não pode esperar que o poço pare sozinho. Ele precisa de acionar remotamente uma válvula de alívio (*choke valve*) ou purga de emergência.
* **Qual é a utilidade?** Permite que o operador execute uma **intervenção corretiva remota em tempo real** diretamente da interface, prevenindo falhas no poço sem precisar de deslocar equipas de manutenção física ao local.
* **Como funciona a lógica por trás do clique?**
  1. O operador clica no botão **"Aliviar Pressão"** no Streamlit.
  2. O Dashboard envia uma requisição `POST` para o endpoint `/poço/{id_poço}/aliviar-pressao` da FastAPI.
  3. A API interseta o estado atual do poço e aplica um algoritmo que força a redução imediata da pressão para níveis operacionais seguros (ex: ~110 - 120 bar).
  4. Na atualização seguinte do Dashboard (segundos depois), a curva de pressão cai drasticamente abaixo da linha dos 150 bar e o estado do poço muda instantaneamente de 🔴 **CRÍTICO** para 🟢 **NORMAL**.

---

## 🚀 Como Executar o Projeto

Podes executar este projeto de **duas formas**: através do **Docker** (recomendado para rodar tudo com um único comando) ou **Manualmente via Python** (instalando as dependências do `requirements.txt`).

---

### 🐳 Opção A: Execução via Docker (Recomendada)

Com o Docker, **não precisas de instalar o `requirements.txt` na tua máquina física**. O Docker cria ambientes isolados, instala as dependências internamente e inicia a API, o Simulador e o Dashboard simultaneamente.

1. **Clonar o repositório:**
   ```bash
   git clone [https://github.com/eduardovianga23-j/telemetria-poço-offshore.git](https://github.com/eduardovianga23-j/telemetria-poço-offshore.git)
   cd telemetria-poço-offshore