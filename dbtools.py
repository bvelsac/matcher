"""Creating and migrating the database with Alembic.

`python manage.py init-db` creates a new database or brings an existing one up to date
(migrations/versions). A change to models.py comes with a migration: see README.md. The tests
build their tables from the models (db.create_all) and check in tests/test_migrations.py that
the migrations give exactly the same result.
"""
import os

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

ROOT = os.path.dirname(os.path.abspath(__file__))


class OldDatabase(Exception):
    """The database was made before migrations existed and cannot be brought up to date."""


def alembic_config(connection):
    config = Config()
    config.set_main_option("script_location", os.path.join(ROOT, "migrations"))
    config.attributes["connection"] = connection
    return config


def upgrade(engine):
    """Bring the database to the newest version; create it when it is empty."""
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        if tables and "alembic_version" not in tables:
            raise OldDatabase(
                "This database was made by a version of PDC from before migrations (tables: {}). "
                "It cannot be updated; there was no data worth keeping at that stage: move the file away "
                "and run init-db again.".format(", ".join(sorted(tables))))
        command.upgrade(alembic_config(connection), "head")
        connection.commit()


def make_migration(engine, message):
    """Write a new migration from the difference between the models and the database, which has
    to be at the newest version. Review the file before committing it."""
    with engine.connect() as connection:
        command.revision(alembic_config(connection), message=message, autogenerate=True)


def differences(connection, metadata):
    """What the models have that the database lacks, or the other way round (empty when they agree)."""
    from alembic.autogenerate import compare_metadata
    context = MigrationContext.configure(connection, opts={"compare_type": True})
    return compare_metadata(context, metadata)
