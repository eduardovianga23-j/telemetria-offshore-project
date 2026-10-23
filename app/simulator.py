"""Serviço de campo: faz de gateway entre os poços e a API.

Em cada ciclo:
1. vai buscar à API os comandos pendentes e aplica-os aos poços;
2. lê os "sensores" (modelo físico ou replay do Volve);
3. envia as leituras para a API.

A ligação parte sempre do campo para a API, nunca ao contrário: a API não
consegue abrir ligações para dentro da rede industrial.

Uso:  python -m app.simulator
"""
from __future__ import annotations

import os
import time
from collections.abc import Iterable, Iterator
from datetime import datetime

import requests

from app.physics import POCOS_ANGOLA, EstadoPoco
from app.volve import ATRIBUICAO, carregar_producao, dias_de_producao


class ClienteAPI:
    def __init__(self, base_url: str, chave: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.sessao = requests.Session()
        self.sessao.headers["X-API-Key"] = chave
        self.timeout = timeout

    def enviar(self, leitura: dict) -> None:
        r = self.sessao.post(f"{self.base_url}/api/telemetria", json=leitura, timeout=self.timeout)
        r.raise_for_status()

    def retoma(self, fonte: str) -> dict:
        r = self.sessao.get(f"{self.base_url}/api/campo/retoma", params={"fonte": fonte}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def pendentes(self) -> list[dict]:
        r = self.sessao.get(f"{self.base_url}/api/comandos/pendentes", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def confirmar(self, comando_id: int, estado: str, detalhe: str) -> None:
        r = self.sessao.post(
            f"{self.base_url}/api/comandos/{comando_id}/confirmacao",
            json={"estado": estado, "detalhe": detalhe[:255]},
            timeout=self.timeout,
        )
        r.raise_for_status()


def processar_comandos(cliente: ClienteAPI, estados: dict[str, EstadoPoco]) -> None:
    for cmd in cliente.pendentes():
        estado = estados.get(cmd["poco_id"])
        if estado is None:
            cliente.confirmar(cmd["id"], "REJEITADO", "Poço não existe neste campo.")
            continue
        try:
            detalhe = estado.aplicar_comando(cmd["acao"])
            cliente.confirmar(cmd["id"], "EXECUTADO", detalhe)
            print(f"[campo] {cmd['acao']} em {cmd['poco_id']}: {detalhe}")
        except ValueError as e:
            cliente.confirmar(cmd["id"], "REJEITADO", str(e))


def ciclo_simulacao(cliente: ClienteAPI, estados: dict[str, EstadoPoco]) -> list[dict]:
    processar_comandos(cliente, estados)
    leituras = [estado.passo() for estado in estados.values()]
    for leitura in leituras:
        cliente.enviar({**leitura, "fonte": "simulacao"})
    return leituras


def correr_simulacao(cliente: ClienteAPI, intervalo_s: float) -> None:
    estados = {p.poco_id: EstadoPoco.novo(p) for p in POCOS_ANGOLA}
    print(f"[campo] Simulação dos Blocos 17 e 32: {', '.join(estados)}")
    while True:
        try:
            ciclo_simulacao(cliente, estados)
        except requests.RequestException as e:
            print(f"[campo] API indisponível ({e}); nova tentativa em breve.")
        time.sleep(intervalo_s)


def dias_por_enviar(dias: Iterable[list[dict]], retoma: dict) -> Iterator[list[dict]]:
    """Salta os dias que a API já tem; no último dia recebido, envia só os poços em falta."""
    if not retoma.get("ultimo_timestamp"):
        yield from dias
        return
    ultimo = datetime.fromisoformat(retoma["ultimo_timestamp"])
    ja_enviados = set(retoma.get("pocos_no_ultimo", []))
    for leituras in dias:
        dia = datetime.fromisoformat(leituras[0]["timestamp"])
        if dia < ultimo:
            continue
        if dia == ultimo:
            leituras = [l for l in leituras if l["poco_id"] not in ja_enviados]
            if not leituras:
                continue
        yield leituras


def _com_nova_tentativa(funcao, intervalo_s: float):
    while True:
        try:
            return funcao()
        except requests.RequestException as e:
            print(f"[campo] API indisponível ({e}); nova tentativa em breve.")
            time.sleep(intervalo_s)


def correr_volve(cliente: ClienteAPI, caminho: str, intervalo_s: float) -> None:
    df = carregar_producao(caminho)
    print(f"[campo] Replay Volve: {len(df)} leituras de {df['poco_id'].nunique()} poços. {ATRIBUICAO}")
    retoma = _com_nova_tentativa(lambda: cliente.retoma("volve"), intervalo_s)
    if retoma.get("ultimo_timestamp"):
        print(f"[campo] A retomar o replay depois de {retoma['ultimo_timestamp'][:10]}.")
    for leituras in dias_por_enviar(dias_de_producao(df), retoma):
        _com_nova_tentativa(lambda: [cliente.enviar(l) for l in leituras], intervalo_s)
        time.sleep(intervalo_s)
    print("[campo] Replay Volve concluído. O histórico completo está na base de dados.")
    while True:
        time.sleep(3600)


def main() -> None:
    cliente = ClienteAPI(
        os.getenv("BASE_API_URL", "http://127.0.0.1:8000"),
        os.getenv("API_KEY_INGESTAO", "dev-ingestao"),
    )
    intervalo = float(os.getenv("INTERVALO_S", "3"))
    if os.getenv("MODO_DADOS", "simulacao").lower() == "volve":
        correr_volve(cliente, os.getenv("VOLVE_FICHEIRO", "data/volve_producao.csv"), intervalo)
    else:
        correr_simulacao(cliente, intervalo)


if __name__ == "__main__":
    main()
