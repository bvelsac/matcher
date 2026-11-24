"""Identity from Authelia, as in PDC (auth.py of PDC): Caddy passes Remote-User and Remote-Name after
Authelia checked the login. Everyone let in may read; the user ids in PDC2_EDITORS may change data
(decided 24 November 2026). PDC2_AUTH_MODE=dev signs everyone in as PDC2_DEV_USER, for development."""
from flask import current_app
from sqlalchemy.exc import IntegrityError

from pdc2.extensions import db, login_manager
from pdc2.models import User


def _utf8(value):
    """Werkzeug reads headers as Latin-1, Authelia sends UTF-8."""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def editors():
    return {x.strip().lower() for x in current_app.config.get("PDC2_EDITORS", "").split(",") if x.strip()}


@login_manager.request_loader
def load_user_from_request(request):
    cfg = current_app.config
    if cfg["PDC2_AUTH_MODE"] == "dev":
        username, name = cfg["PDC2_DEV_USER"], cfg["PDC2_DEV_NAME"]
    else:
        username = _utf8(request.headers.get("Remote-User", "")).strip()
        name = _utf8(request.headers.get("Remote-Name", "")).strip() or username
    if not username:
        return None
    user = User.query.filter_by(username=username).first()
    if user is None:
        db.session.add(User(username=username, name=name))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        user = User.query.filter_by(username=username).first()
    elif name and user.name != name:
        user.name = name
        db.session.commit()
    user.role = "editor" if username.lower() in editors() else "viewer"
    return user


@login_manager.user_loader
def load_user(user_id):
    return None  # never from the session: every request carries the identity
