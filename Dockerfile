FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    MONIQ_PUBLIC_DEMO=true MONIQ_SERVE_FRONTEND=true MONIQ_COOKIE_SECURE=true MONIQ_GMAIL_DISABLED=true \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PORT=8080
WORKDIR /app
COPY backend/requirements-lock.txt /app/backend/requirements-lock.txt
RUN pip install --no-cache-dir -r backend/requirements-lock.txt \
    && useradd --create-home --uid 10001 moniq
COPY backend/ /app/backend/
COPY data/ /app/data/
COPY --from=frontend /build/frontend/dist /app/frontend/dist
RUN mkdir -p /app/.runtime && chown -R moniq:moniq /app/.runtime
USER 10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8080') + '/api/health', timeout=5)"]
CMD ["sh", "-c", "exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --proxy-headers --no-access-log"]
