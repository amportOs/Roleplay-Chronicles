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

# Push application context
app.app_context().push()

# Import migrate here to avoid circular imports
from flask_migrate import Migrate
migrate = Migrate(app, db)

def wait_for_db(max_retries=5, delay=5):
    """Wait for the database to become available."""
    from sqlalchemy.exc import OperationalError, ProgrammingError
    
    for attempt in range(max_retries):
        try:
            # Try to execute a simple query
            db.session.execute('SELECT 1')
            return True
        except (OperationalError, ProgrammingError) as e:
            if attempt < max_retries - 1:
                print(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max retries reached. Could not connect to the database.")
                return False

def init_db():
    """Initialize the database and create test data if needed."""
    print("Initializing database...")
    
    try:
        # Wait for the database to be available
        if not wait_for_db():
            print("Failed to connect to the database after multiple attempts.")
            sys.exit(1)
        
        # Create all database tables if they don't exist
        print("Creating database tables if they don't exist...")
        db.create_all()
        
        # Only create test data if the database is empty
        from login_app.models import User
        if not User.query.first():
            print("Creating test data...")
            create_test_data()
        
        print("Database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_test_data():
    """Create test data in the database."""
    from login_app.models import User, Campaign, Character
    from werkzeug.security import generate_password_hash
    
    try:
        # Create test user
        user1 = User(
            username='testuser',
            email='test@example.com',
            password_hash=generate_password_hash('test123'),
            created_at=datetime.utcnow()
        )
        db.session.add(user1)
        db.session.commit()
        
        # Create test campaign
        campaign1 = Campaign(
            name='The Lost Mine of Phandelver',
            description='A classic D&D adventure for beginners',
            created_at=datetime.utcnow(),
            user_id=user1.id
        )
        db.session.add(campaign1)
        
        # Create test character
        character1 = Character(
            name='Erevan Moonshadow',
            race='Elf',
            character_class='Wizard',
            level=1,
            user_id=user1.id,
            campaign_id=campaign1.id,
            image='default_character.jpg'
        )
        db.session.add(character1)
        
        # Commit all changes
        db.session.commit()
        print("Test data created successfully!")
        return True
    except Exception as e:
        print(f"Error creating test data: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    if not init_db():
        print("Database initialization failed.")
        sys.exit(1)
