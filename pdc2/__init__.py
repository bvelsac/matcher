"""PDC2: booking occasional staff (GM) for Verslaggeving (docs/pdc2-functional-analysis.md).

A Flask application of its own, next to PDC in this repository, with its own database. Start it with
`flask --app pdc2 run` or `gunicorn "pdc2:create_app()"`.
"""
import os
from datetime import date

from flask import Flask, jsonify, render_template, request
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.engine import Engine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()


def create_app(config_name=None):
    from pdc2.config import config
    from pdc2.extensions import csrf, db, login_manager

    # The stylesheet and images are PDC's, shared (static/ of the repository; PDC2's own under static/pdc2).
    app = Flask(__name__, static_folder=os.path.join(ROOT, "static"), static_url_path="/static")
    app.config.from_object(config[config_name or os.environ.get("PDC2_CONFIG", "production")])
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("PDC2_SECRET_KEY is not set (or use PDC2_CONFIG=development).")
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    from pdc2 import auth  # noqa: F401  (registers the request loader)
    from pdc2.helpers import register_helpers
    from pdc2.views import bp

    register_helpers(app)
    app.register_blueprint(bp)

    @login_manager.unauthorized_handler
    def not_signed_in():
        if request.is_json:
            return jsonify({"error": "Not signed in."}), 401
        return render_template("pdc2/error.html", code=401, message="You are not signed in."), 401

    @app.errorhandler(404)
    def not_found(error):
        return render_template("pdc2/error.html", code=404, message="Page not found."), 404

    @app.context_processor
    def globals_():
        return {"today": date.today(), "logout_url": app.config["PDC2_LOGOUT_URL"],
                "source": app.config["PDC2_SOURCE"], "user": current_user}

    return app
