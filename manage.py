#!/usr/bin/env python3
"""Setup and maintenance commands.

    python manage.py init-db         create the database, or bring it up to date (migrations)
    python manage.py make-migration "text"   write a migration for a change in models.py
    python manage.py backup FILE     write a consistent copy of the database to FILE
    python manage.py sample-data     add fictitious interpreters, meetings and bookings for testing

The database is chosen by APP_CONFIG and the settings in .env (see README.md). There are no
accounts to create: people are identified by Authelia (auth.py).
"""
import argparse
import os
import sqlite3
import sys

import dbtools
import sample_data as sample_data_module
from app import app
from extensions import db
from models import Interpreter, Meeting


OLD_DATABASE = 3  # exit status of init-db for a database from before the migrations (.devcontainer/start.sh)


def init_db(args):
    """Create the database, or bring an existing one to the newest version (migrations/)."""
    try:
        dbtools.upgrade(db.engine)
    except dbtools.OldDatabase as error:
        print(error, file=sys.stderr)
        sys.exit(OLD_DATABASE)
    print("Database is up to date.")


def make_migration(args):
    """Write a migration for the changes in models.py (the database must be at the newest version)."""
    dbtools.make_migration(db.engine, args.message)


def backup(args):
    """SQLite's own backup, which gives a consistent copy while PDC keeps running."""
    url = db.engine.url
    if url.get_backend_name() != "sqlite" or not url.database:
        sys.exit("Backup works on the SQLite database file only.")
    target = os.path.abspath(args.file)
    if os.path.exists(target):
        sys.exit("{} already exists; choose a new file.".format(target))
    source = sqlite3.connect(url.database)
    copy = sqlite3.connect(target)
    with copy:
        source.backup(copy)
    copy.close()
    source.close()
    print("Database copied to {}.".format(target))


def sample_data(args):
    """Fictitious data only - never put real interpreters' details in a repository."""
    if Meeting.query.count() or Interpreter.query.count():
        print("The database already has interpreters or meetings: sample data goes into an empty one, nothing added.")
        return
    sample_data_module.load()
    db.session.commit()
    print("Added fictitious interpreters, rooms, meetings (shaped like spic's export) and bookings.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("init-db", help="create the database or bring it up to date").set_defaults(func=init_db)

    p = commands.add_parser("make-migration", help="write a migration for a change in models.py")
    p.add_argument("message")
    p.set_defaults(func=make_migration)

    p = commands.add_parser("backup", help="copy the database to a new file")
    p.add_argument("file")
    p.set_defaults(func=backup)

    commands.add_parser("sample-data", help="add fictitious test data").set_defaults(func=sample_data)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return
    with app.app_context():
        args.func(args)


if __name__ == "__main__":
    main()
