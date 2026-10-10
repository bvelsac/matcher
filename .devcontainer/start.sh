#!/bin/sh
# Start PDC for a trial in Codespaces. Runs in the foreground, in its own terminal, so
# Codespaces keeps it alive. Safe to run again: tables and sample data are only added once.
set -e
cd "$(dirname "$0")/.."
export APP_CONFIG=development
export DATABASE_URL="${DATABASE_URL:-sqlite:////workspaces/pdc_trial.db}"
python -m pip install --quiet -r requirements.txt
python manage.py init-db
python manage.py sample-data
echo "PDC starts on port 5000: open the Ports tab if the browser does not open by itself."
exec python -m flask --app app run --host 0.0.0.0 --port 5000
