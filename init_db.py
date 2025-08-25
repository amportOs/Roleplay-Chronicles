import os
import sys
from datetime import datetime

# Add the project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Now import the app and db
from login_app import app, db

# Ensure the instance folder exists
os.makedirs('instance', exist_ok=True)

def init_db():
    print("Initializing database...")
    print(f"Database path: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Create all database tables
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
        
        # Verify the tables exist
        from sqlalchemy import inspect
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

if __name__ == "__main__":
    init_db()
