import os
import sys
from datetime import datetime

# Add the project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the create_app function and db
from login_app import create_app, db

# Create the Flask application
app = create_app()

# Ensure the instance folder exists
os.makedirs('instance', exist_ok=True)

def init_db():
    print("Initializing database...")
    
    # Create instance directory if it doesn't exist
    instance_path = os.path.join(os.path.dirname(__file__), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    
    with app.app_context():
        print(f"Database path: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        try:
            # Create all database tables
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
                
        except Exception as e:
            print(f"\nERROR: Failed to initialize database: {str(e)}")
            if 'no such table' in str(e).lower():
                print("This might be because the database file is corrupted or in an invalid state.")
                print("Try deleting the database file and running this script again.")
            return False
            
    return True

if __name__ == "__main__":
    init_db()
