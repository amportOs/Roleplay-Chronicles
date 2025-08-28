import os
from login_app import create_app, db
from flask_migrate import upgrade

# Create the Flask application
app = create_app()

# Initialize database and run migrations
with app.app_context():
    db.create_all()
    # Run migrations if needed
    try:
        upgrade()
    except Exception as e:
        print(f"Migration error: {e}")
        # Continue even if migrations fail the Flask application

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
