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
        
        # Handle the case where the URL has an IPv6 address in it
        if '[' in database_url and ']' in database_url:
            # This is an IPv6 address, we need to handle it specially
            import re
            # Extract the IPv6 part
            ipv6_match = re.search(r'\[([0-9a-fA-F:]+)\]', database_url)
            if ipv6_match:
                ipv6 = ipv6_match.group(1)
                # Replace the IPv6 with a placeholder for parsing
                temp_url = database_url.replace(f'[{ipv6}]', 'ipv6_placeholder')
                
                # Parse the URL with the placeholder
                from urllib.parse import urlparse, parse_qs, urlunparse
                parsed = urlparse(temp_url)
                
                # Rebuild the URL with the original IPv6
                netloc = parsed.netloc.replace('ipv6_placeholder', f'[{ipv6}]')
                
                # Reconstruct the URL
                database_url = urlunparse(parsed._replace(netloc=netloc))
        
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
