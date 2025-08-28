from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_cors import CORS
from urllib.parse import quote_plus
from sqlalchemy.engine import Engine
from sqlalchemy import event
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
    
    # Get database URL from environment variable, fall back to SQLALCHEMY_DATABASE_URI
    database_url = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_DATABASE_URI')
    
    if database_url:
        print("Original DATABASE_URL:", database_url)
        
        # 1. Ensure the scheme is postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
            print("Updated scheme to postgresql://")
        
        # 2. Remove any square brackets from the URL
        if '[' in database_url or ']' in database_url:
            database_url = database_url.replace('[', '').replace(']', '')
            print("Removed square brackets from DATABASE_URL")
        
        # 3. Add sslmode=require if not present
        if 'sslmode' not in database_url:
            if '?' in database_url:
                database_url += '&sslmode=require'
            else:
                database_url += '?sslmode=require'
            print("Added sslmode=require to DATABASE_URL")
            
        print("Processed DATABASE_URL:", database_url)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback to SQLite for local development
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    
    # Disable track modifications to suppress warning
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate.init_app(app, db)
    
    # Configure CORS
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Import and register blueprints
    from .auth import auth as auth_blueprint
    from .main import main as main_blueprint
    from .characters import characters as characters_blueprint
    from .campaigns import campaigns as campaigns_blueprint
    
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(characters_blueprint, url_prefix='/characters')
    app.register_blueprint(campaigns_blueprint, url_prefix='/campaigns')
    
    # Initialize database and run migrations
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created/verified")
        except Exception as e:
            print(f"Error creating database tables: {str(e)}")
            # Re-raise the exception to fail the startup if database connection fails
            raise
    
    return app
