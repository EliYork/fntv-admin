FROM node:22-alpine AS frontend-builder
WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

LABEL org.opencontainers.image.source="https://github.com/EliYork/fntv-admin" \
      org.opencontainers.image.description="Docker Compose-first Feiniu TV enhanced admin console" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

COPY backend/requirements.txt ./requirements.txt
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y tzdata \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY scripts/audit_fntv_time_chain.py ./scripts/audit_fntv_time_chain.py
COPY --from=frontend-builder /frontend/dist ./app/static

RUN mkdir -p /data/logs /data/cache /data/backup /fntv

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-proxy-headers"]
