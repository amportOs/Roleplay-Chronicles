import os
import os
from login_app import create_app, db
from flask_migrate import Migrate, upgrade

def initialize_database(app):
    with app.app_context():
        try:
            # Create migrations directory if it doesn't exist
            migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
            if not os.path.exists(migrations_dir):
                print("Creating migrations directory...")
                os.makedirs(migrations_dir)
            
            # Initialize Flask-Migrate
            migrate = Migrate()
            migrate.init_app(app, db, directory=migrations_dir)
            
            # Create tables if they don't exist
            db.create_all()
            print("Database tables verified")
            
            # Run migrations
            upgrade(directory=migrations_dir)
            print("Database migrations completed")
            
        except Exception as e:
            print(f"Database initialization error: {str(e)}")
            # Don't fail hard in production, but log the error
            if os.environ.get('FLASK_ENV') == 'development':
                raise

# Create the Flask application
app = create_app()

# Initialize database and run migrations
initialize_database(app)

# This file is used by Gunicorn in production
# The application factory pattern is used to create the app instance

if __name__ == "__main__":
    # This block is only executed when running the script directly
    debug = os.environ.get('FLASK_DEBUG', '0').lower() in ['1', 'true', 'yes']
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=debug)
else:
    # This block is executed when imported (e.g., by gunicorn)
    # Ensure the application context is available
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
