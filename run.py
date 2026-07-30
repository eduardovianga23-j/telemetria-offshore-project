import time
import random
import requests

# Endereço da API dentro do mesmo ambiente/container
API_URL = "http://localhost:8000/api/telemetria"

def simular_telemetria():
    """Função que gera e envia dados de telemetria continuamente."""
    pocos = ["POCO-01", "POCO-02", "POCO-03"]
    
    print("🤖 Loop do simulador iniciado...")
    
    while True:
        try:
            for poco in pocos:
                # Simula oscilações de pressão, temperatura e vazão
                dados = {
                    "poco_id": poco,
                    "pressao_bar": round(random.uniform(100.0, 160.0), 2),
                    "temperatura_celsius": round(random.uniform(50.0, 90.0), 2),
                    "vazao_m3h": round(random.uniform(30.0, 80.0), 2)
                }
                
                # Envia os dados para a API
                response = requests.post(API_URL, json=dados, timeout=5)
                
            # Aguarda 3 segundos antes de gerar a próxima leitura
            time.sleep(3)
            
        except Exception as e:
            print(f"⚠️ Erro no simulador (tentando novamente em 5s): {e}")
            time.sleep(5)

# Bloco executado apenas se rodar o ficheiro diretamente via terminal
if __name__ == "__main__":
    simular_telemetria()