FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 (PostgreSQL 클라이언트 + MCP runtime + Codex CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    nodejs \
    npm \
    && npm install -g mcporter @openai/codex \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치 (캐시 활용을 위해 먼저 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY . .

ENV ENV=production

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/api/v1/health')"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 9000"]
