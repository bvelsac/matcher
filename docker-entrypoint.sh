#!/bin/sh
# Wait until the database accepts connections and create any missing tables,
# then start the command given by the Dockerfile (gunicorn).
set -e

tries=0
max_tries="${DB_WAIT_TRIES:-30}"
until python manage.py init-db; do
    tries=$((tries + 1))
    if [ "$tries" -ge "$max_tries" ]; then
        echo "The database is still not reachable after $max_tries attempts; stopping." >&2
        exit 1
    fi
    echo "Database not ready yet ($tries/$max_tries), retrying in 2 seconds..." >&2
    sleep 2
done

exec "$@"
