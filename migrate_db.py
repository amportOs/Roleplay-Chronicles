import os
from flask_migrate import Migrate, upgrade, migrate as migrate_db, init, stamp
from login_app import create_app, db

def run_migrations():
    app = create_app()
    
    # Set up migrations directory
    basedir = os.path.abspath(os.path.dirname(__file__))
    migrations_dir = os.path.join(basedir, 'migrations')
    
    with app.app_context():
        # Initialize Flask-Migrate
        migrate = Migrate()
        migrate.init_app(app, db, directory=migrations_dir)
        
        # Initialize migrations if needed
        if not os.path.exists(os.path.join(migrations_dir, 'env.py')):
            print("Initializing migrations...")
            init(directory=migrations_dir)
            
            # Create initial migration
            print("Creating initial migration...")
            migrate_db(directory=migrations_dir, message="Initial migration")
            
            # Stamp the database with the current migration
            stamp(directory=migrations_dir)
        
        # Apply any pending migrations
        print("Applying migrations...")
        upgrade(directory=migrations_dir)
        
        print("Database migrations completed successfully!")

if __name__ == "__main__":
    run_migrations()
