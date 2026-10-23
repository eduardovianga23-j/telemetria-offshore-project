# O que mudou na versão 2 e porquê

Este documento explica cada mudança, para que consigas defender o projeto
numa entrevista. Lê-o com o código aberto ao lado.

## 1. Erros corrigidos

| Problema na v1 | O que foi feito | Onde |
|---|---|---|
| Havia dois simuladores (`run.py` e `app/simulator.py`) com nomes de poços diferentes, e o filtro do dashboard ficava vazio | Um só simulador; o dashboard pede a lista de poços à API (`/api/pocos`) em vez de a ter escrita no código | `app/simulator.py`, `app/dashboard.py` |
| O botão "Aliviar pressão" reescrevia a última leitura guardada | O comando muda o **estado do poço**. As leituras antigas nunca são alteradas | `app/physics.py` (`aplicar_comando`), `app/main.py` |
| O dashboard falava em Isolation Forest, mas o modelo não estava ligado | O modelo é treinado com os dados da BD e avalia cada nova leitura (coluna `anomalia_ml`) | `app/ml_engine.py`, `app/main.py` |
| Os dados viviam numa lista em memória e perdiam-se ao reiniciar | SQLite num volume Docker; pronto a trocar por PostgreSQL/TimescaleDB mudando só `DB_URL` | `app/database.py`, `docker-compose.yml` |
| Limite de "ATENÇÃO" diferente na API (135) e no README (130) | Uma só regra, configurável, usada por todo o sistema | `app/config.py` (`classificar_pressao`) |
| Custo do flare calculado com o caudal de **petróleo**, em euros | Indicador "Produção em risco" (o que se perde se o poço parar), em USD por barril | `app/dashboard.py` |
| Termos brasileiros ("vazão", "Controle", "Gêmeo") | Português de Portugal e Angola: caudal, controlo | Todo o projeto |

## 2. Dados com comportamento físico

Na v1, cada leitura era sorteada ao acaso: a pressão podia saltar de 158 para
102 bar em 3 segundos. Agora (`app/physics.py`):

- **Inércia:** a pressão percorre 15% do caminho até ao valor alvo em cada
  passo. É um modelo de primeira ordem, o mesmo tipo de modelo usado em
  controlo de processos.
- **Picos que decaem:** simulam golfadas de gás. É isto que gera os alertas.
- **Física ligada:** caudal proporcional à raiz quadrada do diferencial de
  pressão no choke (como numa válvula real) e temperatura que acompanha o
  caudal.
- **Alívio realista:** a pressão desce ao longo de vários passos, não de uma
  vez, e parte do caudal é desviado.

Frase para entrevista: *"Os dados simulados seguem um modelo de primeira
ordem com perturbações, por isso os alertas e o efeito dos comandos são
credíveis, e os testes verificam que não há saltos impossíveis."*

## 3. Separação entre monitorização e controlo

É a mudança mais importante, e liga diretamente à conversa sobre IT e OT.

- **Fila de comandos:** a consola cria um comando (`PENDENTE`); o campo vai
  buscá-lo, aplica-o e confirma (`EXECUTADO` ou `REJEITADO`). A ligação parte
  sempre do campo. É o mesmo princípio de um Cloudflare Tunnel.
- **Duas chaves de API:** a de ingestão (o campo) e a de controlo (a
  consola). O dashboard de monitorização não tem nenhuma.
- **Dois dashboards a partir do mesmo código:** `monitor` (porta 8501, só
  leitura) e `consola` (porta 8502, presa a `127.0.0.1`).
- **Auditoria:** cada comando guarda operador, hora de criação e hora de
  execução.

Frase para entrevista: *"Separei a monitorização, que pode ser publicada
com uma camada de acesso, da atuação, que fica na rede local. Os comandos
passam por uma fila auditada e o campo é que os vai buscar, para nunca abrir
portas de entrada na rede industrial."*

## 4. Modo Volve

`MODO_DADOS=volve` faz replay dos dados reais de produção diária do Volve.
Os dados não vão para o Git (licença da Equinor). No modo Volve os comandos
são recusados, porque não faz sentido atuar sobre o passado.

## 5. Qualidade e DevOps

- **26 testes** com pytest: API, segurança das chaves, ciclo de vida dos
  comandos, física, leitor do Volve e um teste de ponta a ponta entre o campo
  e a API.
- **CI a sério:** corre os testes, constrói a imagem Docker e arranca o
  sistema para confirmar que a telemetria chega à API.
- **Docker:** uma só imagem para todos os serviços, utilizador sem
  privilégios de root, healthcheck na API e versões fixadas.
- **Configuração por `.env`:** nenhuma chave no código.

## O que ainda não está feito (e está no plano de estudo)

TimescaleDB, MQTT, Prometheus e Grafana, Terraform e a publicação com
Cloudflare Tunnel e Access.
