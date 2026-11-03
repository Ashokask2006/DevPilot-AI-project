# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.lock ./
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -f /run/secrets/proxy_ca ]; then \
      PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.lock; \
    else \
      pip install --no-cache-dir -r requirements.lock; \
    fi

RUN groupadd --gid 10001 devpilot \
    && useradd --uid 10001 --gid devpilot --create-home --shell /usr/sbin/nologin devpilot \
    && mkdir -p /data/workspaces \
    && chown -R devpilot:devpilot /app /data

COPY --chown=devpilot:devpilot app ./app

USER devpilot

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
