"""PDC2's migrations give the database its models describe."""
from sqlalchemy import create_engine, text

import dbtools
from pdc2.__main__ import LOCATION
from pdc2.extensions import db


def test_the_migrations_of_pdc2_match_its_models(pdc2_app, tmp_path):
    engine = create_engine("sqlite:///{}".format(tmp_path / "pdc2.db"))
    try:
        dbtools.upgrade(engine, LOCATION)
        dbtools.upgrade(engine, LOCATION)           # twice changes nothing
        with engine.connect() as connection:
            assert dbtools.differences(connection, db.metadata) == []
            triggers = {r[0] for r in connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'trigger'"))}
            indexes = {r[0] for r in connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'index'"))}
        assert triggers == {"log_no_update", "log_no_delete"}
        assert "uq_bookings_active_half_day" in indexes
    finally:
        engine.dispose()
