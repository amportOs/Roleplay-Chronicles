import os
import sys
from flask_migrate import upgrade, migrate as migrate_db, init, stamp
from login_app import create_app, db

def run_migrations():
    app = create_app()
    
    # Set up migrations directory
    basedir = os.path.abspath(os.path.dirname(__file__))
    migrations_dir = os.path.join(basedir, 'migrations')
    
    # Ensure migrations directory exists
    os.makedirs(migrations_dir, exist_ok=True)
    
    with app.app_context():
        # Initialize migrations if needed
        if not os.path.exists(os.path.join(migrations_dir, 'env.py')):
            print("Initializing migrations...")
            try:
                init(directory=migrations_dir)
                print("Created migrations directory at:", migrations_dir)
                
                # Create initial migration
                print("Creating initial migration...")
                migrate_db(directory=migrations_dir, message="Initial migration")
                
                # Stamp the database with the current migration
                stamp(directory=migrations_dir)
                print("Database stamped with initial migration.")
            except Exception as e:
                print(f"Error initializing migrations: {e}")
                sys.exit(1)
        
        # Apply any pending migrations
        print("Applying migrations...")
        try:
            upgrade(directory=migrations_dir)
            print("Migrations applied successfully!")
        except Exception as e:
            print(f"Error applying migrations: {e}")
            sys.exit(1)

def create_tables():
    """Create database tables directly if migrations fail"""
    app = create_app()
    with app.app_context():
        try:
            print("Creating database tables directly...")
            db.create_all()
            print("Database tables created successfully!")
            return True
        except Exception as e:
            print(f"Error creating tables: {e}")
            return False

if __name__ == "__main__":
    # First try running migrations
    try:
        run_migrations()
    except Exception as e:
        print(f"Migration failed: {e}")
        print("Falling back to direct table creation...")
        if not create_tables():
            print("Failed to create tables. Please check your database connection.")
            sys.exit(1)
