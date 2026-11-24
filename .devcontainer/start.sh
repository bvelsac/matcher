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
# PDC2 next to it, on port 5001, with fictitious data for spic and the jaarkalender (PDC2_SOURCE=fake).
export PDC2_CONFIG=development
export PDC2_DATABASE_URL="${PDC2_DATABASE_URL:-sqlite:////workspaces/pdc2_trial.db}"
python -m pdc2 init-db
python -m pdc2 sample-data
python -m flask --app pdc2 run --host 0.0.0.0 --port 5001 &
echo "PDC2 starts on port 5001."
echo "PDC starts on port 5000: open the Ports tab if the browser does not open by itself."
exec python -m flask --app app run --host 0.0.0.0 --port 5000
