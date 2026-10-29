FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Least privilege: run as non-root; the SQLite store needs a writable data dir.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /srv/app/data /data \
    && chown -R appuser:appuser /srv/app /data
USER appuser

EXPOSE 8000

# Single worker per container; Valkey-backed limits are shared, so scale out via replicas.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"

CMD ["uvicorn", "--factory", "app.api.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
