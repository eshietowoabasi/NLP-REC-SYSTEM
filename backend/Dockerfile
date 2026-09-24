# Backend image, shared by the API (Gunicorn) and the RQ worker.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Downloaded NLP models (SBERT) are cached on a named volume.
    HF_HOME=/data/models

# libmagic: content-type detection of uploads (python-magic).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd --create-home --uid 1000 appuser

COPY requirements.txt requirements-dev.txt ./
ARG INSTALL_DEV=false
RUN pip install --upgrade pip setuptools \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install -r requirements-dev.txt; \
       else pip install -r requirements.txt; fi

COPY . .
RUN mkdir -p /data/storage /data/models && chown -R appuser:appuser /app /data

USER appuser
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "wsgi:app"]
