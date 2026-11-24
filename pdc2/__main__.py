"""Commands of PDC2.

    python -m pdc2 init-db                 create the database, or bring it up to date (migrations)
    python -m pdc2 make-migration "text"   write a migration for a change in pdc2/models.py
    python -m pdc2 sample-data             fictitious GMs, offers and bookings, for trying PDC2 out
    python -m pdc2 backup FILE             a consistent copy of the database

PDC2_CONFIG and the PDC2_* settings choose the database (see README.md).
"""
import argparse
import os
import sqlite3
import sys

import dbtools
from pdc2 import create_app
from pdc2.extensions import db

LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
OLD_DATABASE = 3


def init_db(args):
    try:
        dbtools.upgrade(db.engine, LOCATION)
    except dbtools.OldDatabase as error:
        print(error, file=sys.stderr)
        sys.exit(OLD_DATABASE)
    print("Database is up to date.")


def make_migration(args):
    dbtools.make_migration(db.engine, args.message, LOCATION)


def sample_data(args):
    from pdc2.models import Gm
    from pdc2.sample_data import load
    if Gm.query.count():
        print("The database already has GMs: sample data goes into an empty one, nothing added.")
        return
    load()
    db.session.commit()
    print("Added fictitious GMs, offers and bookings.")


def backup(args):
    url = db.engine.url
    if url.get_backend_name() != "sqlite" or not url.database:
        sys.exit("Backup works on the SQLite database file only.")
    target = os.path.abspath(args.file)
    if os.path.exists(target):
        sys.exit("{} already exists; choose a new file.".format(target))
    source, copy = sqlite3.connect(url.database), sqlite3.connect(target)
    with copy:
        source.backup(copy)
    copy.close()
    source.close()
    print("Database copied to {}.".format(target))


def main():
    parser = argparse.ArgumentParser(prog="python -m pdc2", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("init-db").set_defaults(func=init_db)
    p = commands.add_parser("make-migration")
    p.add_argument("message")
    p.set_defaults(func=make_migration)
    commands.add_parser("sample-data").set_defaults(func=sample_data)
    p = commands.add_parser("backup")
    p.add_argument("file")
    p.set_defaults(func=backup)
    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return
    with create_app().app_context():
        args.func(args)


if __name__ == "__main__":
    main()
