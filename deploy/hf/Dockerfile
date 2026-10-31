# Asset Intelligence - Hugging Face Space image (single container).
# Local validation (repo root): docker build -f deploy/hf/Dockerfile -t asset-intel-space .
#   docker run -p 7860:7860 --env-file .env asset-intel-space
# Space repo: this file is synced to the Space root; the build context is the
# repo root in both places, so every COPY path below is repo-relative.

# ---- UI build ----
FROM node:22-alpine AS uibuild
WORKDIR /ui
COPY app/ui/package.json app/ui/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY app/ui/ ./
RUN npm run build

# ---- Runtime: API + nginx under supervisord, UID 1000 (Spaces contract) ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STORE_PATH=/home/user/app/data/inspections.db \
    RATE_LIMIT_STORAGE_URI=memory://
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 user \
    && mkdir -p /home/user/app/data /data /tmp/nginx-space/body /tmp/nginx-space/proxy /tmp/nginx-space/fastcgi /tmp/nginx-space/uwsgi /tmp/nginx-space/scgi \
    && chown -R user:user /home/user /data /tmp/nginx-space
WORKDIR /home/user/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY --from=uibuild /ui/dist /usr/share/nginx/html
COPY deploy/hf/supervisord.conf /etc/supervisor/conf.d/space.conf
COPY deploy/hf/nginx-space.conf /etc/nginx/space.conf
USER user
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/')"
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/space.conf"]
