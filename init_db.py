import os
import sys
import time
from datetime import datetime
from urllib.parse import urlparse

# Add the project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Now import the app and db
from login_app import create_app, db

# Create the Flask application
app = create_app()

def wait_for_db(max_retries=5, delay=5):
    """Wait for the database to become available."""
    from sqlalchemy.exc import OperationalError
    
    for attempt in range(max_retries):
        try:
            with app.app_context():
                # Try to execute a simple query
                db.session.execute('SELECT 1')
                print("Database connection successful!")
                return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max retries reached. Could not connect to the database.")
                return False

def init_db():
    print("Initializing database...")
    
    # Parse database URL for logging (without password)
    db_url = urlparse(app.config['SQLALCHEMY_DATABASE_URI'])
    safe_url = f"{db_url.scheme}://{db_url.hostname}:{db_url.port}{db_url.path}"
    print(f"Connecting to database: {safe_url}")
    
    # Wait for database to be available
    if not wait_for_db():
        print("Failed to connect to the database. Exiting.")
        sys.exit(1)
    
    # Create all database tables
    with app.app_context():
        try:
            print("Creating database tables...")
            db.create_all()
            print("Database tables created successfully!")
            
            # Verify the tables exist
            from sqlalchemy import inspect, text
            
            # Test the connection with a raw query
            try:
                db.session.execute(text('SELECT 1'))
                print("Database connection is working.")
            except Exception as e:
                print(f"Error executing test query: {str(e)}")
            
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print("\nTables in database:", tables)
            
            # Check for required tables
            required_tables = ['user', 'campaign', 'character', 'message', 'post', 'npc', 'quest', 'session']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"\nWARNING: The following tables are missing: {', '.join(missing_tables)}")
                print("Please check your model definitions and database configuration.")
            else:
                print("\nAll required tables exist!")
                
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            # Print more detailed error information
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    init_db()
