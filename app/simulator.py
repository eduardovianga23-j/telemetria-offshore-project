import requests
import random
import time

API_URL = "http://127.0.0.1:8000/api/telemetria"
POCOS = ["Poco_Bloco17_A", "Poco_Bloco17_B", "Poco_Bloco32_C"]

while True:
    poco = random.choice(POCOS)
    # Simula flutuações com picos ocasionais
    pressao = round(random.uniform(120.0, 158.0), 2)
    temp = round(random.uniform(70.0, 85.0), 2)
    vazao = round(random.uniform(400.0, 450.0), 2)

    payload = {
        "poco_id": poco,
        "pressao_bar": pressao,
        "temperatura_celsius": temp,
        "vazao_m3h": vazao
    }

    try:
        res = requests.post(API_URL, json=payload)
        print(f"Enviado: {poco} | Pressão: {pressao} bar -> Resposta BD: {res.status_code}")
    except Exception as e:
        print(f"Erro ao enviar: {e}")

    time.sleep(3) # Envia a cada 3 segundos