from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'

def create_app():
    from .app import create_app
    return create_app()

# Import models to ensure they are registered with SQLAlchemy
from . import models
