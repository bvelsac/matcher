#!/usr/bin/env python3
"""Setup and maintenance commands.

    python manage.py init-db         create the database tables
    python manage.py backup FILE     write a consistent copy of the database to FILE
    python manage.py sample-data     add fictitious interpreters and meetings for testing

The database is chosen by APP_CONFIG and the settings in .env (see README.md). There are no
accounts to create: people are identified by Authelia (auth.py).
"""
import argparse
import os
import sqlite3
import sys
from datetime import date, time, timedelta

from app import app
from extensions import db
from models import Interpreter, Meeting, User


def init_db(args):
    db.create_all()
    print("Database tables created (existing tables are left untouched).")


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
    owner = User.query.filter_by(username="sample-data").first()
    if not owner:
        owner = User(username="sample-data", name="Sample data")
        db.session.add(owner)
        db.session.flush()

    if Interpreter.query.count() == 0:
        people = [
            ("Agence", "Alpha", "planning@alpha-bureau.example", "Bureau Alpha", "English, German"),
            ("Bureau", "Beta", "contact@beta-bureau.example", "Bureau Beta", "English, Spanish"),
            ("Anna", "Peeters", "anna.peeters@example.org", "", "English"),
            ("Luc", "Dubois", "luc.dubois@example.org", "", "English, Italian"),
            ("Sarah", "Janssens", "sarah.janssens@example.org", "", ""),
        ]
        for position, (first, last, email, bureau, languages) in enumerate(people, start=1):
            db.session.add(Interpreter(
                first_name=first,
                last_name=last,
                email=email,
                bureau_affiliation=bureau,
                priority_order=position,
                additional_languages=languages,
            ))
        print("Added {} fictitious interpreters.".format(len(people)))

    if Meeting.query.count() == 0:
        monday = date.today() + timedelta(days=7 - date.today().weekday())
        db.session.add_all([
            Meeting(name="Uitgebreid Bureau / Bureau élargi", date=monday, time=time(12, 0),
                    estimated_duration=2, interpreters_needed=1, location="Room 1",
                    category="parliament", created_by=owner.id),
            Meeting(name="Bureau", date=monday + timedelta(days=2), time=time(12, 15),
                    estimated_duration=2, interpreters_needed=1, location="Room 1",
                    category="parliament", created_by=owner.id),
            Meeting(name="Committee hearing", date=monday + timedelta(days=3), time=time(9, 30),
                    estimated_duration=3, interpreters_needed=3, location="Room 2",
                    category="external_group", created_by=owner.id),
        ])
        print("Added 3 sample meetings for next week.")

    db.session.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("init-db", help="create the database tables").set_defaults(func=init_db)

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
