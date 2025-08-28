from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_cors import CORS
import os
from urllib.parse import urlparse

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cors = CORS()

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
    
    # Get database URL from environment variable
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        print("Original DATABASE_URL:", database_url)
        
        # Ensure the scheme is postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # Check if this is a direct Supabase connection (IPv6) and convert to connection pooler
        if 'db.' in database_url and '.supabase.co' in database_url:
            # Extract the project ref and password from the original URL
            import re
            from urllib.parse import urlparse, parse_qs, urlunparse
            
            # Parse the original URL to get the password
            parsed = urlparse(database_url)
            username = parsed.username or ''
            password = parsed.password or ''
            
            # Extract the project ref from the hostname
            match = re.search(r'db\.([a-zA-Z0-9]+)\.supabase\.co', parsed.hostname or '')
            if match and password:
                project_ref = match.group(1)
                # Construct the connection pooler URL with the original password
                database_url = f"postgresql://postgres.{project_ref}:{password}@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
                print("Converted to connection pooler URL")
            else:
                print("Warning: Could not extract project ref or password from DATABASE_URL")
        
        # Add sslmode=require if not present
        if 'sslmode=' not in database_url:
            if '?' in database_url:
                database_url += '&sslmode=require'
            else:
                database_url += '?sslmode=require'
                
        print("Processed DATABASE_URL:", database_url)
        
        # Configure SQLAlchemy with connection pooling and SSL
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_timeout': 30,
            'pool_size': 5,
            'max_overflow': 10,
            'connect_args': {
                'connect_timeout': 10,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            }
        }
    else:
        # Fallback to SQLite if no database URL is provided
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    from .auth import auth as auth_blueprint
    from .main import main as main_blueprint
    
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
