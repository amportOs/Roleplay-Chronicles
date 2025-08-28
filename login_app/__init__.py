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
            username = parsed.username or 'postgres'  # Default to 'postgres' if not specified
            password = parsed.password or ''
            
            # Extract the project ref from the hostname
            match = re.search(r'db\.([a-zA-Z0-9]+)\.supabase\.co', parsed.hostname or '')
            if match and password:
                project_ref = match.group(1)
                
                # Ensure the username is in the correct format for the connection pooler
                if not username.startswith('postgres.'):
                    username = f'postgres.{project_ref}'
                
                # Construct the connection pooler URL with the original password
                database_url = f"postgresql://{username}:{password}@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
                print(f"Converted to connection pooler URL with username: {username}")
            else:
                print("Warning: Could not extract project ref or password from DATABASE_URL")
        # If already using the pooler but with wrong format, fix the username
        elif 'pooler.supabase.com' in database_url and '@aws-' in database_url:
            parsed = urlparse(database_url)
            username = parsed.username or ''
            password = parsed.password or ''
            
            if not username.startswith('postgres.') and '.' not in username:
                # Extract project ref from the username if possible
                project_ref = username.split('@')[0] if '@' in username else 'your_project_ref'
                new_username = f'postgres.{project_ref}'
                # Reconstruct the URL with the correct username
                netloc = f"{new_username}:{password}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                database_url = urlunparse(parsed._replace(netloc=netloc))
                print(f"Updated pooler URL with correct username format: {new_username}")
        
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
