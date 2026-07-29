# SmartCart — AI-Powered Shopping Cart System
# Multi-purpose image: FastAPI storefront+API on :8904 (default), optional Streamlit on :8501

FROM python:3.12-slim

LABEL org.opencontainers.image.title="SmartCart" \
      org.opencontainers.image.description="AI-powered shopping cart — FastAPI + SQLite/Postgres" \
      org.opencontainers.image.source="https://github.com/sharanyashwant27-tech/SmartCart---AI-Powered-Shopping-Cart-System-Python" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8904 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/logs /app/uploads /app/static \
    && chmod -R a+rX /app

EXPOSE 8904 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8904/health', timeout=3)"

# Default: FastAPI storefront + API (web UI at http://localhost:8904)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8904"]
