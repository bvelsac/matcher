"""Flask extensions, created once here and bound to the app in app.py.

Keeping them in their own module avoids the circular import between
app.py and models.py.
"""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
