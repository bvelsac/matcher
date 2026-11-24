"""Alembic environment of PDC2: migrations run on a connection that dbtools.py hands over."""
from alembic import context

import pdc2.models  # noqa: F401  (registers the tables on PDC2's metadata)
from pdc2.extensions import db

config = context.config
connection = config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Run migrations through `python -m pdc2 init-db`.")

context.configure(connection=connection, target_metadata=db.metadata, render_as_batch=True, compare_type=True)
with context.begin_transaction():
    context.run_migrations()
