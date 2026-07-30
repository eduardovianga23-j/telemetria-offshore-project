import subprocess
import sys
import time

def run_app():
    print("🚀 A iniciar a API FastAPI...")
    # Aponta para o módulo app.main em vez de main
    api_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "app.main:app", "--reload"
    ])

    time.sleep(2)

    print("📊 A iniciar o Dashboard Streamlit...")
    # Aponta para o caminho app/dashboard.py em vez de dashboard.py
    streamlit_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "app/dashboard.py"
    ])

    try:
        api_process.wait()
        streamlit_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 A encerrar aplicação...")
        api_process.terminate()
        streamlit_process.terminate()

if __name__ == "__main__":
    run_app()