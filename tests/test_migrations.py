"""The migrations (migrations/versions) give the same database as the models."""
import pytest
from sqlalchemy import create_engine, inspect, text

import dbtools
from extensions import db
from models import APPEND_ONLY_TABLES


@pytest.fixture
def engine(app, tmp_path):
    """A new SQLite file, with the same settings as the application's (foreign keys on)."""
    engine = create_engine("sqlite:///{}".format(tmp_path / "pdc.db"))
    yield engine
    engine.dispose()


def test_the_migrations_build_exactly_what_the_models_describe(engine):
    dbtools.upgrade(engine)
    with engine.connect() as connection:
        assert dbtools.differences(connection, db.metadata) == [], "make a migration: python manage.py make-migration"
        triggers = {row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'trigger'"))}
    assert triggers == {"{}_no_{}".format(t, v) for t in APPEND_ONLY_TABLES for v in ("update", "delete")}


def test_upgrading_twice_changes_nothing(engine):
    dbtools.upgrade(engine)
    dbtools.upgrade(engine)
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert version == "0001"


def test_the_log_is_append_only_in_a_migrated_database_too(engine):
    dbtools.upgrade(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO assignment_log (recorded_at, user_name, action) VALUES ('2030-01-01', 'x', 'proposed')"))
    with pytest.raises(Exception, match="append-only"):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM assignment_log"))


def test_a_database_from_before_the_migrations_is_not_touched(engine):
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE meetings (id INTEGER PRIMARY KEY, name TEXT)"))
    with pytest.raises(dbtools.OldDatabase, match="before migrations"):
        dbtools.upgrade(engine)
    assert "alembic_version" not in inspect(engine).get_table_names()
