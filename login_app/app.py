from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort, jsonify, session
from flask_login import LoginManager, current_user
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
import os
import uuid
from .extensions import db, login_manager, migrate, cors
from .models import User, init_db
from .auth import auth as auth_blueprint
from .main import main as main_blueprint
from .storage import allowed_file, upload_file, delete_file
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configure the application
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Session lasts 30 days
    
    # File upload configuration
    app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
    app.config['CHARACTER_IMAGES'] = 'static/character_images'
    app.config['CAMPAIGN_IMAGES'] = 'static/campaign_images'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    # Register blueprints
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)
    
    # Create upload directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CHARACTER_IMAGES'], exist_ok=True)
    os.makedirs(app.config['CAMPAIGN_IMAGES'], exist_ok=True)
    
    # Initialize database
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        init_db()
    
    # Add proxy fix if behind a reverse proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
