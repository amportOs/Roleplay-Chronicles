from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_cors import CORS
import os
from urllib.parse import urlparse, parse_qs, urlunparse, quote_plus
import re

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()  # Will be initialized with app later
cors = CORS()

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
    
    # Get database URL from environment variable
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        print("Original DATABASE_URL:", database_url)
        
        # Clean up the database URL
        print("Original DATABASE_URL:", database_url)
        
        # 1. Ensure the scheme is postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
            print("Updated scheme to postgresql://")
        
        # 2. Remove any square brackets from the URL
        if '[' in database_url or ']' in database_url:
            database_url = database_url.replace('[', '').replace(']', '')
            print("Removed square brackets from DATABASE_URL")
        
        # 3. Extract and properly encode the password
        if '@' in database_url:
            # Split into user:pass@host and path parts
            auth_part, rest = database_url.split('@', 1)
            if '://' in auth_part:
                scheme, auth_part = auth_part.split('://', 1)
            else:
                scheme = 'postgresql'
            
            # Handle user:password format
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
                # URL encode the password
                encoded_password = quote_plus(password)
                # Rebuild the URL with encoded password
                auth_part = f"{username}:{encoded_password}"
            
            # Rebuild the full URL
            database_url = f"{scheme}://{auth_part}@{rest}"
            print("Processed and encoded DATABASE_URL credentials")
        
        # Parse the URL to handle both direct and pooler connections
        parsed = urlparse(database_url)
        username = parsed.username or 'postgres'
        password = parsed.password or ''
        
        # Handle direct Supabase connection (IPv6)
        if 'db.' in database_url and '.supabase.co' in database_url:
            # Extract the project ref from the hostname
            match = re.search(r'db\.([a-zA-Z0-9]+)\.supabase\.co', parsed.hostname or '')
            if match and password:
                project_ref = match.group(1)
                username = f'postgres.{project_ref}'
                hostname = 'aws-1-eu-central-1.pooler.supabase.com'
                port = 5432
                print(f"Converted direct Supabase URL to connection pooler format")
            else:
                print("Warning: Could not extract project ref or password from DATABASE_URL")
                return None
        # Handle connection pooler URL
        elif 'pooler.supabase.com' in database_url:
            hostname = parsed.hostname
            port = parsed.port or 5432
        else:
            print("Warning: Unsupported database URL format")
            return None
        
        # URL encode the password to handle special characters
        if password:
            encoded_password = quote_plus(password)
            # Rebuild the URL with encoded password
            netloc = f"{username}:{encoded_password}@{hostname}"
            if port:
                netloc += f":{port}"
            database_url = urlunparse(parsed._replace(netloc=netloc, scheme='postgresql'))
            print("Processed database URL with encoded credentials")
        
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
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    # Initialize migrate with both app and db
    global migrate
    migrate = Migrate(app, db)
    cors.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
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
