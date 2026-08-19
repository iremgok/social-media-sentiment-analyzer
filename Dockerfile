# Hafif resmi Python imajı
FROM python:3.11-slim

# Python davranışlarını optimize et
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem bağımlılıklarını güncelle
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları kopyala ve kur (Cache optimizasyonu için)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm proje kodlarını kopyala
COPY . .

# Varsayılan portları tanımla (Backend: 8000, Streamlit: 8501)
EXPOSE 8000 8501