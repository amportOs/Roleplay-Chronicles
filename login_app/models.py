from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .supabase_client import get_supabase

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(255), primary_key=True)  # Using UUID as string
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=True)
    full_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_pic = db.Column(db.String(100), default='default.jpg')
    password_hash = db.Column(db.String(100), nullable=True)  # Only for local auth fallback
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    profile_updated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    characters = db.relationship('Character', backref='user', lazy=True)
    dm_campaigns = db.relationship('Campaign', backref='dm', lazy=True, foreign_keys='Campaign.dm_id')
    player_campaigns = db.relationship('Campaign', secondary='player_campaign', backref='players')
    messages = db.relationship('Message', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password) if self.password_hash else False
    
    @classmethod
    def get_or_create_from_supabase(cls, user_data):
        """Get or create a user from Supabase auth data"""
        user = cls.query.filter_by(id=user_data.id).first()
        
        if not user:
            # Create a new user
            user = cls(
                id=user_data.id,
                email=user_data.email,
                username=user_data.user_metadata.get('username') or user_data.email.split('@')[0],
                is_approved=False  # Default to False, admin needs to approve
            )
            db.session.add(user)
            
        # Update user data
        user.email = user_data.email
        user.last_login = datetime.utcnow()
        
        db.session.commit()
        return user

# Define other models as before, but with Supabase-compatible types
class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    system = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100), default='default_campaign.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    dm_id = db.Column(db.String(255), db.ForeignKey('users.id'), nullable=False)
    
    def has_access(self, user):
        """Check if user has access to this campaign"""
        return self.dm_id == user.id or user in self.players
    
    def get_character_for_user(self, user_id):
        """Get the character for a user in this campaign"""
        return Character.query.filter_by(
            user_id=user_id, 
            campaign_id=self.id
        ).first()

# Association table for many-to-many relationship between users and campaigns
player_campaign = db.Table('player_campaign',
    db.Column('user_id', db.String(255), db.ForeignKey('users.id'), primary_key=True),
    db.Column('campaign_id', db.String(255), db.ForeignKey('campaigns.id'), primary_key=True)
)

class Character(db.Model):
    __tablename__ = 'characters'
    
    id = db.Column(db.String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(255), db.ForeignKey('users.id'), nullable=False)
    campaign_id = db.Column(db.String(255), db.ForeignKey('campaigns.id'), nullable=False)
    character_name = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(100), nullable=False, default='')
    character_class = db.Column(db.String(50), nullable=True)
    level = db.Column(db.Integer, nullable=True)
    race = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_image_url(self):
        if self.image and not self.image.startswith(('http://', 'https://')):
            return url_for('static', filename=f'character_images/{self.image}')
        return self.image or url_for('static', filename='images/default_character.jpg')

# Add other models (NPC, Quest, Message, etc.) with similar updates
# ...

def init_db():
    """Initialize the database"""
    db.create_all()
    
    # Create admin user if not exists
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            id=str(uuid.uuid4()),
            email=admin_email,
            username='admin',
            is_admin=True,
            is_approved=True,
            profile_updated=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"Created admin user: {admin_email}")
    
    return admin
