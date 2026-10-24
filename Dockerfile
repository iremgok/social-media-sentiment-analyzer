FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# CPU sürümü torch (CUDA'lı sürümden ~2 GB daha küçük imaj)
COPY requirements.txt .
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY src ./src

RUN useradd --create-home appuser && mkdir -p /app/data /app/.cache && chown -R appuser /app
USER appuser

EXPOSE 8000 8501

# Varsayılan komut backend'i başlatır; dashboard docker-compose'da ayrı serviste çalışır.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
