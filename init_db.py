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
    """Initialize the database and create test data if needed."""
    print("Initializing database...")
    
    # Wait for the database to be available
    if not wait_for_db():
        print("Failed to connect to the database after multiple attempts.")
        sys.exit(1)
    
    try:
        # Create all database tables
        print("Creating database tables...")
        with app.app_context():
            db.create_all()
            
            # Only create test data if the database is empty
            from login_app.models import User
            if not User.query.first():
                print("Creating test data...")
                create_test_data()
            
            print("Database initialized successfully!")
            
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def create_test_data():
    """Create test data in the database."""
    from login_app.models import User, Campaign, Character
    
    # Create test user
    user1 = User(
        username='testuser',
        email='test@example.com',
        password='test123',  # Will be hashed by the User model
        profile_pic='default.jpg',
        bio='Test user bio',
        is_admin=False
    )
    db.session.add(user1)
    
    # Create test campaign
    campaign1 = Campaign(
        title='Test Campaign',
        description='A test campaign',
        game_master_id=1,
        image='default_campaign.jpg',
        is_public=True
    )
    db.session.add(campaign1)
    
    # Create test character
    character1 = Character(
        name='Test Character',
        race='Human',
        character_class='Fighter',
        level=1,
        user_id=1,
        campaign_id=1,
        image='default_character.jpg'
    )
    db.session.add(character1)
    
    # Commit all changes
    db.session.commit()
    print("Test data created successfully!")

if __name__ == "__main__":
    init_db()
