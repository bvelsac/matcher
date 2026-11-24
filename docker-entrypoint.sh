#!/bin/sh
# Create the SQLite database on the volume, or bring it up to date with the migrations,
# then start the command given by the Dockerfile (gunicorn).
set -e
# The same image runs PDC and PDC2 (PDC_APP=pdc2), each with its own database.
if [ "${PDC_APP:-pdc}" = "pdc2" ]; then
    python -m pdc2 init-db
else
    python manage.py init-db
fi
exec "$@"
