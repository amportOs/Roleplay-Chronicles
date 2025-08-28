from flask import Flask
from .extensions import db, login_manager, cors, get_supabase
from .models import User
from .auth import auth as auth_blueprint
from .main import main as main_blueprint
from .characters import characters as characters_blueprint
from .campaigns import campaigns as campaigns_blueprint
import os
from datetime import timedelta

def create_app():
    app = Flask(__name__)
    
    # Configure the application
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    
    # File upload configuration
    app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
    app.config['CHARACTER_IMAGES'] = 'static/character_images'
    app.config['CAMPAIGN_IMAGES'] = 'static/campaign_images'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    cors.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
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
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    return app
