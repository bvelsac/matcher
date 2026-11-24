"""Fictitious GMs, offers and bookings for trying PDC2 out (with PDC2_SOURCE=fake for spic and the
jaarkalender). Every name is invented; never put real people here."""
import random
from datetime import date, timedelta

from pdc2 import fake, rules
from pdc2.extensions import db
from pdc2.models import User

GMS = [
    # first name, last name, languages, standard role, other roles
    ("Ann", "Aerts", ["nl"], "redacteur", ["revisor"]),
    ("Bram", "Bosmans", ["nl"], "redacteur", []),
    ("Cato", "Coolen", ["nl"], "revisor", ["redacteur"]),
    ("Daan", "De Smet", ["nl"], "redacteur", []),
    ("Eva", "Engels", ["nl", "fr"], "redacteur", ["revisor", "vertaler"]),
    ("Fanny", "Fontaine", ["fr"], "redacteur", ["revisor"]),
    ("Gilles", "Gérard", ["fr"], "redacteur", []),
    ("Hélène", "Hubert", ["fr"], "revisor", ["redacteur"]),
    ("Inès", "Istace", ["fr"], "redacteur", []),
    ("Jules", "Jacquet", ["fr"], "redacteur", ["revisor"]),
    ("Karim", "Koné", ["fr"], "redacteur", []),
    ("Lotte", "Lemmens", ["nl"], "redacteur", ["revisor"]),
]


def load(today=None):
    today = today or date.today()
    user = User.query.filter_by(username="sample-data").first()
    if user is None:
        user = User(username="sample-data", name="Sample data")
        db.session.add(user)
        db.session.flush()
    gms = []
    for first, last, languages, role, others in GMS:
        email = "{}.{}@example.org".format(first, last).lower().replace(" ", "").replace("é", "e").replace("è", "e")
        gms.append(rules.save_gm(None, {"first_name": first, "last_name": last, "email": email, "languages": languages,
                                        "standard_role": role, "roles": others, "active": True}, user))
    # Offers for this week and the next three: each GM offers about half of the half-days.
    monday = fake.monday_of(today)
    rng = random.Random(monday.toordinal())
    for week in range(4):
        for offset in range(5):
            day = monday + timedelta(days=7 * week + offset)
            if not fake.is_workday(day):
                continue
            for gm in gms:
                for period in ("AM", "PM"):
                    if rng.random() < 0.45:
                        rules.offer(gm, day, period, user, source="import")
    # A few bookings this week, one confirmed.
    from pdc2.models import Offer
    first_offers = Offer.query.filter(Offer.date >= monday, Offer.date < monday + timedelta(days=5)) \
        .order_by(Offer.date, Offer.period, Offer.gm_id).limit(3).all()
    for number, offer in enumerate(first_offers):
        booking = rules.book(offer.gm, offer.date, offer.period, offer.gm.standard_role, offer.gm.languages[0], user)
        if number == 0:
            rules.confirm(booking, user)
