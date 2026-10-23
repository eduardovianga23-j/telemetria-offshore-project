# Uma só imagem para os três papéis (API, campo e dashboards).
# O comando de cada serviço é definido no docker-compose.yml.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Não correr como root dentro do contentor
RUN useradd --create-home --uid 1000 twin \
    && mkdir -p /data \
    && chown -R twin:twin /app /data
USER twin

EXPOSE 8000 8501
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
