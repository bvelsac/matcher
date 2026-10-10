"""Alembic environment: migrations always run on a connection that dbtools.py hands over."""
from alembic import context

import models  # noqa: F401  (registers the tables on the metadata)
from extensions import db

config = context.config
connection = config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Run migrations through `python manage.py init-db` (see dbtools.py).")

context.configure(connection=connection, target_metadata=db.metadata, render_as_batch=True, compare_type=True)
with context.begin_transaction():
    context.run_migrations()
