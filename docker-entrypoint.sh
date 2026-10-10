#!/bin/sh
# Create any missing tables in the SQLite database on the volume,
# then start the command given by the Dockerfile (gunicorn).
set -e
python manage.py init-db
exec "$@"
