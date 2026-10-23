"""Modelo físico simplificado de um poço produtor offshore.

Não é um simulador de reservatório: é um modelo de primeira ordem, suficiente
para que os dados se comportem de forma credível.

- A pressão na cabeça do poço tem inércia: aproxima-se de um valor alvo aos
  poucos, em vez de saltar de leitura para leitura.
- Surgem picos de pressão ocasionais (por exemplo, golfadas de gás) que
  decaem com o tempo.
- O caudal depende da abertura do choke e da pressão disponível.
- A temperatura acompanha o caudal: mais caudal, fluido mais quente à superfície.
- O comando ALIVIAR_PRESSAO abre uma válvula de alívio (bypass) durante algum
  tempo. A pressão desce gradualmente e parte do caudal é desviada.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

PRESSAO_SEPARADOR_BAR = 20.0  # pressão a jusante do choke


@dataclass
class ParametrosPoco:
    poco_id: str
    pressao_base_bar: float  # pressão de equilíbrio com o choke de referência
    caudal_ref_m3h: float  # caudal com o choke de referência e a pressão base
    temperatura_base_c: float
    choke_ref_pct: float = 45.0
    prob_pico: float = 0.012  # probabilidade de começar um pico em cada passo
    pico_max_bar: float = 62.0


@dataclass
class EstadoPoco:
    param: ParametrosPoco
    pressao_bar: float
    temperatura_c: float
    choke_pct: float
    pico_bar: float = 0.0
    passos_alivio: int = 0  # >0 enquanto a válvula de alívio está aberta
    rng: random.Random = field(default_factory=random.Random, repr=False)

    # Constantes do modelo
    INERCIA = 0.15  # fração do caminho até ao alvo percorrida em cada passo
    DECAIMENTO_PICO = 0.97
    QUEDA_ALIVIO_BAR = 40.0
    DESVIO_ALIVIO = 0.30  # fração do caudal desviada durante o alívio
    DURACAO_ALIVIO = 20  # passos

    @classmethod
    def novo(cls, param: ParametrosPoco, seed: int | None = None) -> "EstadoPoco":
        return cls(
            param=param,
            pressao_bar=param.pressao_base_bar,
            temperatura_c=param.temperatura_base_c,
            choke_pct=param.choke_ref_pct,
            rng=random.Random(seed),
        )

    @property
    def alivio_ativo(self) -> bool:
        return self.passos_alivio > 0

    # --- Comandos vindos da sala de controlo -------------------------------
    def aplicar_comando(self, acao: str) -> str:
        if acao == "ALIVIAR_PRESSAO":
            self.passos_alivio = self.DURACAO_ALIVIO
            return f"Válvula de alívio aberta durante {self.DURACAO_ALIVIO} passos."
        if acao == "REPOR_NORMAL":
            self.passos_alivio = 0
            return "Válvula de alívio fechada."
        raise ValueError(f"Ação desconhecida: {acao}")

    # --- Um passo de simulação ---------------------------------------------
    def passo(self) -> dict:
        p = self.param
        rng = self.rng

        # Picos ocasionais de pressão que decaem
        if self.pico_bar < 1.0 and rng.random() < p.prob_pico:
            self.pico_bar = rng.uniform(0.5, 1.0) * p.pico_max_bar
        self.pico_bar *= self.DECAIMENTO_PICO

        # Pressão alvo: abrir o choke baixa a pressão a montante
        alvo = p.pressao_base_bar + self.pico_bar - 0.6 * (self.choke_pct - p.choke_ref_pct)
        if self.alivio_ativo:
            alvo -= self.QUEDA_ALIVIO_BAR
            self.passos_alivio -= 1

        self.pressao_bar += self.INERCIA * (alvo - self.pressao_bar) + rng.gauss(0, 0.6)
        self.pressao_bar = max(self.pressao_bar, PRESSAO_SEPARADOR_BAR + 1)

        # Caudal: depende da abertura do choke e do diferencial de pressão
        dp = max(self.pressao_bar - PRESSAO_SEPARADOR_BAR, 1.0)
        dp_ref = p.pressao_base_bar - PRESSAO_SEPARADOR_BAR
        caudal = p.caudal_ref_m3h * (self.choke_pct / p.choke_ref_pct) ** 0.8 * math.sqrt(dp / dp_ref)
        if self.alivio_ativo:
            caudal *= 1 - self.DESVIO_ALIVIO
        caudal *= 1 + rng.gauss(0, 0.01)

        # Temperatura: acompanha o caudal, com inércia térmica
        temp_alvo = p.temperatura_base_c + 0.12 * (caudal - p.caudal_ref_m3h)
        self.temperatura_c += 0.2 * (temp_alvo - self.temperatura_c) + rng.gauss(0, 0.2)

        return {
            "poco_id": p.poco_id,
            "pressao_bar": round(self.pressao_bar, 2),
            "temperatura_celsius": round(self.temperatura_c, 2),
            "caudal_oleo_m3h": round(max(caudal, 0.0), 2),
            "abertura_choke_pct": round(self.choke_pct, 1),
        }


# Poços fictícios inspirados em poços de águas profundas dos Blocos 17 e 32.
# Os valores são plausíveis, não reais.
POCOS_ANGOLA: list[ParametrosPoco] = [
    ParametrosPoco("B17-A", pressao_base_bar=118.0, caudal_ref_m3h=95.0, temperatura_base_c=78.0),
    ParametrosPoco("B17-B", pressao_base_bar=112.0, caudal_ref_m3h=80.0, temperatura_base_c=74.0, prob_pico=0.016, pico_max_bar=55.0),
    ParametrosPoco("B32-C", pressao_base_bar=122.0, caudal_ref_m3h=110.0, temperatura_base_c=82.0, pico_max_bar=55.0),
]
