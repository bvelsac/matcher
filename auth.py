"""Identity from Authelia and rights (functional analysis 9, point 3).

PDC sits behind Caddy and Authelia, like spic. Caddy has every request checked
by Authelia and then passes Remote-User and Remote-Name. PDC trusts those
headers because the container is only reachable through Caddy: never publish
its port directly, and only put trusted containers on the infracriv network.

There are no passwords in PDC. Each request carries the identity; the user is
recorded in the users table the first time it is seen, so meetings and the
log can refer to it.

Rights: everyone Authelia lets in may read. Who may change data will come
from spic's list of invoerders and beheerders, once spic offers it; until
then the user ids in PDC_EDITORS may change data.

For development without Authelia: PDC_AUTH_MODE=dev, with PDC_DEV_USER and
PDC_DEV_NAME.
"""
from flask import current_app
from sqlalchemy.exc import IntegrityError

from extensions import db, login_manager
from models import User


def _utf8(value):
    """Werkzeug reads header values as Latin-1 while Authelia sends UTF-8; without this a name
    with an accent arrives garbled. A value that is already right stays as it is."""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def editors():
    return {x.strip().lower() for x in current_app.config.get("PDC_EDITORS", "").split(",") if x.strip()}


def role_for(username):
    return "editor" if username.lower() in editors() else "viewer"


@login_manager.request_loader
def load_user_from_request(request):
    cfg = current_app.config
    if cfg["PDC_AUTH_MODE"] == "dev":
        username, name = cfg["PDC_DEV_USER"], cfg["PDC_DEV_NAME"]
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
        except IntegrityError:  # a parallel request recorded the same user first
            db.session.rollback()
        user = User.query.filter_by(username=username).first()
    elif name and user.name != name:
        user.name = name
        db.session.commit()
    user.role = role_for(username)
    return user


@login_manager.user_loader
def load_user(user_id):
    # Identity is never kept in the session; every request carries it (see above).
    return None
