# Python 3.12, the same version as spic on the same server.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_CONFIG=production

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10002 matcher \
    && mkdir -p /data && chown matcher /data   # the SQLite database lives on this volume
USER matcher

EXPOSE 8000
# The entrypoint creates missing tables, then starts gunicorn.
ENTRYPOINT ["sh", "docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "app:app"]
