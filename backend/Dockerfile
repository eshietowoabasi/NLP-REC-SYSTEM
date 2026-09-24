FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    NUMBA_CACHE_DIR=/tmp/numba-cache

WORKDIR /app

# hdbscan builds a C extension on some platforms.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Current packaging tools (older pip/setuptools have published advisories).
RUN python -m pip install --upgrade pip setuptools

# CPU-only PyTorch first, so sentence-transformers does not pull CUDA wheels.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the SBERT model into the image so production needs no internet access.
ARG SBERT_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENV SBERT_MODEL=${SBERT_MODEL}
RUN python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['SBERT_MODEL'])"

COPY . .

RUN useradd --create-home appuser && mkdir -p /data/raw /data/reports && chown -R appuser /app /data /opt/hf-cache
USER appuser

ENV FLASK_APP=wsgi.py \
    UPLOAD_FOLDER=/data/raw \
    HF_HUB_OFFLINE=1

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "wsgi:app"]
