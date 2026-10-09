#!/usr/bin/env python3
"""Setup and maintenance commands.

    python manage.py init-db         create the database tables
    python manage.py create-user     add a user (prompts for the password)
    python manage.py set-password    change a user's password
    python manage.py sample-data     add fictitious interpreters and meetings for testing

The database is chosen by APP_CONFIG and the settings in .env (see README.md).
"""
import argparse
import getpass
import sys
from datetime import date, time, timedelta

from werkzeug.security import generate_password_hash

from app import app
from extensions import db
from models import Interpreter, Meeting, User


def ask_password():
    while True:
        first = getpass.getpass("Password: ")
        if len(first) < 8:
            print("Use at least 8 characters.")
            continue
        if first == getpass.getpass("Repeat password: "):
            return first
        print("Passwords do not match, try again.")


def init_db(args):
    db.create_all()
    print("Database tables created (existing tables are left untouched).")


def create_user(args):
    username = args.username or input("Username: ").strip()
    email = args.email or input("Email: ").strip()
    role = args.role or input("Role (editor/viewer): ").strip().lower()
    if role not in ("editor", "viewer"):
        sys.exit("Role must be 'editor' or 'viewer'.")
    if User.query.filter((User.username == username) | (User.email == email)).first():
        sys.exit("A user with this username or email already exists.")
    user = User(
        username=username,
        email=email,
        role=role,
        password_hash=generate_password_hash(ask_password()),
    )
    db.session.add(user)
    db.session.commit()
    print("User '{}' created with role '{}'.".format(username, role))


def set_password(args):
    username = args.username or input("Username: ").strip()
    user = User.query.filter_by(username=username).first()
    if not user:
        sys.exit("No user named '{}'.".format(username))
    user.password_hash = generate_password_hash(ask_password())
    db.session.commit()
    print("Password changed for '{}'.".format(username))


def sample_data(args):
    """Fictitious data only - never put real interpreters' details in a repository."""
    owner = User.query.filter_by(role="editor").first()
    if not owner:
        sys.exit("Create an editor first: python manage.py create-user")

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

    p = commands.add_parser("create-user", help="add a user")
    p.add_argument("--username")
    p.add_argument("--email")
    p.add_argument("--role", choices=["editor", "viewer"])
    p.set_defaults(func=create_user)

    p = commands.add_parser("set-password", help="change a user's password")
    p.add_argument("--username")
    p.set_defaults(func=set_password)

    commands.add_parser("sample-data", help="add fictitious test data").set_defaults(func=sample_data)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return
    with app.app_context():
        args.func(args)


if __name__ == "__main__":
    main()
