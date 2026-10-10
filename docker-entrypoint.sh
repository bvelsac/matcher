#!/bin/sh
# Create the SQLite database on the volume, or bring it up to date with the migrations,
# then start the command given by the Dockerfile (gunicorn).
set -e
python manage.py init-db
exec "$@"
