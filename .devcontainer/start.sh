#!/bin/sh
# Start PDC for a trial in Codespaces. Runs in the foreground, in its own terminal, so
# Codespaces keeps it alive. Safe to run again: the database is brought up to date and sample data is only added once.
set -e
cd "$(dirname "$0")/.."
export APP_CONFIG=development
export DATABASE_URL="${DATABASE_URL:-sqlite:////workspaces/pdc_trial.db}"
python -m pip install --quiet -r requirements.txt
# A trial database from before the migrations (exit status 3) has another model and no data worth
# keeping: start afresh. Any other failure stops the script.
status=0
python manage.py init-db || status=$?
if [ "$status" -eq 3 ]; then
    rm -f "${DATABASE_URL#sqlite:///}"*
    python manage.py init-db
elif [ "$status" -ne 0 ]; then
    exit "$status"
fi
python manage.py sample-data
echo "PDC starts on port 5000: open the Ports tab if the browser does not open by itself."
exec python -m flask --app app run --host 0.0.0.0 --port 5000
