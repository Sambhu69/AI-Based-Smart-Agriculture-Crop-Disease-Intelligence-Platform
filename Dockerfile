# Lean production image for Smart Agriculture Platform FastAPI Backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:///./smart_ag.db \
    APP_ENV=production \
    LOG_LEVEL=INFO

WORKDIR /app

# Install minimal runtime shared libraries for Pillow/OpenCV-headless if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt \
    sqlalchemy>=2.0.0 \
    alembic>=1.13.0 \
    pydantic-settings>=2.0.0 \
    python-multipart>=0.0.9 \
    networkx>=3.0

# Copy application code & migrations (exclude datasets/weights via .dockerignore)
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app/ ./app/
COPY pipelines/ ./pipelines/
COPY src/ ./src/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
