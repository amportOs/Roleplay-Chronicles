from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from . import db, login_manager
from .models import User, Post  # Import models from models.py
import os
import time
import uuid
from datetime import datetime
from sqlalchemy import or_, func

def create_app():
    app = Flask(__name__)
    
    # Configure the application
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
    
    # Use SQLite database
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # File upload configuration
    app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
    app.config['CHARACTER_IMAGES'] = 'static/character_images'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Initialize database
    with app.app_context():
        try:
            # Ensure the instance folder exists
            os.makedirs('instance', exist_ok=True)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            os.makedirs(app.config['CHARACTER_IMAGES'], exist_ok=True)
            
            # Import models to ensure they are registered with SQLAlchemy
            from login_app import models
            
            # Create database tables
            db.create_all()
            
        except Exception as e:
            app.logger.error(f"Error initializing database: {str(e)}")
            # If this is production and using PostgreSQL, re-raise the error
            if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql://'):
                raise
    
    return app

# Create the app instance
app = create_app()

# Helper function
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

import os
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    full_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_pic = db.Column(db.String(100), default='default.jpg')
    password = db.Column(db.String(100), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    profile_updated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    
    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('messages', lazy=True))
    campaign = db.relationship('Campaign', backref=db.backref('messages', lazy=True, order_by='Message.timestamp'))
    character = db.relationship('Character', backref=db.backref('messages', lazy=True))

class NPC(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    race = db.Column(db.String(50))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    appearance = db.Column(db.Text)
    personality = db.Column(db.Text)
    background = db.Column(db.Text)
    notes = db.Column(db.Text)
    tags = db.Column(db.Text)
    is_important = db.Column(db.Boolean, default=False)
    image = db.Column(db.String(100), default='default_npc.jpg')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f"NPC('{self.name}', '{self.race}')"

class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    reward = db.Column(db.Text)
    status = db.Column(db.String(20), default='open')  # open, in_progress, done
    priority = db.Column(db.String(20), default='normal')  # low, normal, high
    is_main = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    campaign = db.relationship('Campaign', backref=db.backref('quests', lazy=True))

    def __repr__(self):
        return f"Quest('{self.title}', status='{self.status}')"

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    title = db.Column(db.String(120))
    scheduled_at = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(120))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    campaign = db.relationship('Campaign', backref=db.backref('sessions', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_sessions', lazy=True))

    def __repr__(self):
        return f"Session('{self.title or 'Session'}' at {self.scheduled_at})"

# RSVP responses per session and user
class SessionResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    response = db.Column(db.String(10), nullable=False)  # 'yes', 'no', 'maybe'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Constraints
    __table_args__ = (
        db.UniqueConstraint('session_id', 'user_id', name='uq_session_user'),
    )

    # Relationships
    session = db.relationship('Session', backref=db.backref('responses', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('session_responses', lazy=True))

# Polls for proposing multiple session times
class SessionPoll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    title = db.Column(db.String(150))
    notes = db.Column(db.Text)
    is_closed = db.Column(db.Boolean, default=False, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    campaign = db.relationship('Campaign', backref=db.backref('polls', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_polls', lazy=True))

class SessionPollOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('session_poll.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(120))
    notes = db.Column(db.Text)

    poll = db.relationship('SessionPoll', backref=db.backref('options', lazy=True, cascade='all, delete-orphan'))

class SessionPollVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option_id = db.Column(db.Integer, db.ForeignKey('session_poll_option.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    response = db.Column(db.String(10), nullable=False)  # 'yes', 'no', 'maybe'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('option_id', 'user_id', name='uq_poll_option_user'),
    )

    option = db.relationship('SessionPollOption', backref=db.backref('votes', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('poll_votes', lazy=True))

# Association table for many-to-many relationship between users and campaigns
player_campaign = db.Table('player_campaign',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('campaign_id', db.Integer, db.ForeignKey('campaign.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=datetime.utcnow)
)

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    character_name = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(100), nullable=False, default='')
    character_class = db.Column(db.String(50), nullable=True)
    level = db.Column(db.Integer, nullable=True)
    race = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('characters', lazy=True))
    campaign = db.relationship('Campaign', backref=db.backref('characters', lazy=True))
    
    def get_image_url(self):
        if self.image:
            return url_for('static', filename=f'character_images/{self.image}')
        return url_for('static', filename='character_images/default_character.jpg')

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    system = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100), default='default_campaign.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    dm_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dm = db.relationship('User', backref=db.backref('dm_campaigns', lazy=True))
    players = db.relationship('User', secondary=player_campaign, 
                             backref=db.backref('player_campaigns', lazy=True))
    
    def has_access(self, user):
        """Check if user has access to this campaign"""
        return user.id == self.dm_id or user in self.players
        
    def get_character_for_user(self, user_id):
        """Get the character for a user in this campaign, or None if not found"""
        return Character.query.filter_by(
            user_id=user_id,
            campaign_id=self.id
        ).first()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def home():
    if not current_user.profile_updated:
        flash('Bitte vervollständige dein Profil, bevor du fortfährst.', 'info')
        return redirect(url_for('profile'))
    
    # Get campaigns where user is DM or player
    dm_campaigns = Campaign.query.filter_by(dm_id=current_user.id).all()
    player_campaigns = current_user.player_campaigns
    
    # Combine and deduplicate campaigns
    all_campaigns = list({campaign.id: campaign for campaign in dm_campaigns + player_campaigns}.values())
    
    # Sort by creation date (newest first)
    all_campaigns.sort(key=lambda x: x.created_at, reverse=True)

    # Upcoming sessions across user's campaigns
    campaign_ids = [c.id for c in all_campaigns]
    upcoming_sessions = []
    if campaign_ids:
        upcoming_sessions = (
            Session.query
            .filter(Session.campaign_id.in_(campaign_ids), Session.scheduled_at >= datetime.now())
            .order_by(Session.scheduled_at.asc())
            .limit(10)
            .all()
        )
    
    campaign_names = {c.id: c.name for c in all_campaigns}
    
    # Get all characters for the current user
    characters = Character.query.filter_by(user_id=current_user.id).all()
    
    # Create a dictionary of campaign_id -> character for quick lookup
    characters_by_campaign = {char.campaign_id: char for char in characters}
    
    return render_template('home.html', 
                         campaigns=all_campaigns, 
                         upcoming_sessions=upcoming_sessions, 
                         campaign_names=campaign_names,
                         characters_by_campaign=characters_by_campaign)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # If user is already logged in but hasn't completed their profile, redirect them
        if not current_user.profile_updated:
            flash('Please complete your profile to continue.', 'info')
            return redirect(url_for('profile'))
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_approved:
                flash('Your account is pending admin approval. You will receive an email once your account is approved.', 'warning')
                return redirect(url_for('login'))
                
            login_user(user, remember=True)
            
            # Check if user needs to complete their profile
            if not user.profile_updated:
                flash('Welcome! Please complete your profile to continue.', 'info')
                return redirect(url_for('profile'))
                
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, is_approved=False)
        
        # First user becomes admin and auto-approved
        if User.query.count() == 0:
            new_user.is_admin = True
            new_user.is_approved = True
        
        db.session.add(new_user)
        db.session.commit()
        
        if new_user.is_approved:
            flash('Registration successful! Please log in.')
        else:
            flash('Registration successful! Please wait for admin approval.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/post', methods=['POST'])
@login_required
def create_post():
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            post = Post(content=content, user_id=current_user.id, timestamp=datetime.utcnow())
            db.session.add(post)
            db.session.commit()
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin():
    print(f"[DEBUG] Admin access attempt by user: {current_user.username}, is_admin: {current_user.is_admin}")
    # Only allow admin users to access this page
    if not current_user.is_admin:
        print("[DEBUG] Access denied - user is not an admin")
        flash('You do not have permission to access the admin panel.', 'danger')
        return redirect(url_for('home'))
    
    try:
        print("[DEBUG] Attempting to fetch pending users...")
        # Get all users who are not approved yet, ordered by registration date (newest first)
        pending_users = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
        print(f"[DEBUG] Found {len(pending_users)} pending users")
        
        # Get system statistics
        print("[DEBUG] Fetching system statistics...")
        total_users = User.query.count()
        active_users = User.query.filter_by(is_approved=True).count()
        total_posts = Post.query.count()
        print(f"[DEBUG] Stats - Total: {total_users}, Active: {active_users}, Posts: {total_posts}")
        
        # Test template rendering with minimal data
        print("[DEBUG] Attempting to render template...")
        return render_template(
            'admin.html',
            pending_users=pending_users or [],
            total_users=total_users,
            active_users=active_users,
            total_posts=total_posts
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[ERROR] Admin panel error: {str(e)}\n{error_details}")
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('home'))
        return redirect(url_for('home'))

@app.route('/approve_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def approve_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f'User {user.username} has been approved!', 'success')
    return redirect(url_for('admin'))

@app.route('/reject_user/<int:user_id>', methods=['POST'])
@login_required
def reject_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'User {username} has been rejected and removed from the system.', 'success')
    return redirect(url_for('admin'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Get post count for the current user
    post_count = Post.query.filter_by(user_id=current_user.id).count()
    
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name', '').strip()
        # Handle email - set to None if empty to avoid UNIQUE constraint violation
        email = request.form.get('email', '').strip()
        current_user.email = email if email else None
        current_user.bio = request.form.get('bio', '').strip()
        
        # Handle profile picture upload
        if 'profile_pic' in request.files and request.files['profile_pic'].filename != '':
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                # Delete old profile picture if it exists and is not the default
                if current_user.profile_pic and current_user.profile_pic != 'default.jpg':
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_pic))
                    except Exception as e:
                        print(f"Error deleting old profile picture: {e}")
                
                # Save new profile picture
                filename = secure_filename(f"{current_user.id}_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_pic = filename
                current_user.profile_updated = True
        
        # Handle password change if provided
        current_password = request.form.get('current_password')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if current_password or new_password or confirm_password:
            if not current_password or not new_password or not confirm_password:
                flash('Please fill in all password fields to change your password.', 'danger')
            elif not check_password_hash(current_user.password, current_password):
                flash('Current password is incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match!', 'danger')
            else:
                current_user.password = generate_password_hash(new_password, method='sha256')
                flash('Password updated successfully!', 'success')
        
        # Mark profile as updated if this is the first time
        if not current_user.profile_updated:
            current_user.profile_updated = True
            db.session.commit()
            flash('Profile completed successfully!', 'success')
            return redirect(url_for('home'))
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', post_count=post_count)

@app.route('/profile_pic/<filename>')
def profile_pic(filename):
    return send_from_directory(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), filename)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/check_db')
def check_db():
    try:
        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Check if user table exists and get admin users
        admin_users = []
        if 'user' in [t.lower() for t in tables]:
            admin_users = User.query.filter_by(is_admin=True).all()
        
        return f"""
        <h1>Database Status</h1>
        <p>Tables: {', '.join(tables)}</p>
        <h2>Admin Users:</h2>
        <ul>
            {"".join([f"<li>{u.username} (ID: {u.id}, Email: {u.email})</li>" for u in admin_users])}
        </ul>
        <p><a href="/make_admin/YOUR_USERNAME">Make a user admin</a> (replace YOUR_USERNAME)</p>
        """
    except Exception as e:
        return f"Error checking database: {str(e)}"

@app.route('/make_admin/<username>')
def make_admin(username):
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            user.is_admin = True
            user.is_approved = True
            db.session.commit()
            return f"User {username} is now an admin! <a href='/admin'>Go to Admin Panel</a>"
        return f"User {username} not found!"
    except Exception as e:
        return f"Error making user admin: {str(e)}"

# Route to create a new campaign
@app.route('/create_campaign', methods=['POST'])
@login_required
def create_campaign():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        system = request.form.get('system')
        
        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.root_path, 'static/campaign_images', filename))
            else:
                filename = 'default_campaign.jpg'
        else:
            filename = 'default_campaign.jpg'
        
        # Create new campaign
        campaign = Campaign(
            name=name,
            description=description,
            system=system,
            image=filename,
            dm_id=current_user.id
        )
        
        db.session.add(campaign)
        db.session.commit()
        
        flash('Kampagne erfolgreich erstellt!', 'success')
        return redirect(url_for('home'))
    
    return redirect(url_for('home'))

# Common RPG systems for the dropdown
COMMON_SYSTEMS = [
    'Dungeons & Dragons 5e',
    'Das Schwarze Auge',
    'Call of Cthulhu',
    'Shadowrun',
    'Pathfinder',
    'Starfinder',
    'Warhammer Fantasy',
    'Splittermond',
    'Midgard',
    'Andere'
]

@app.context_processor
def inject_common_systems():
    return dict(common_systems=COMMON_SYSTEMS)

@app.route('/campaigns')
@login_required
def campaigns():
    # Get all campaigns where user is DM or player
    dm_campaigns = Campaign.query.filter_by(dm_id=current_user.id).all()
    player_campaigns = current_user.player_campaigns
    
    # Combine and deduplicate campaigns
    all_campaigns = list({campaign.id: campaign for campaign in dm_campaigns + player_campaigns}.values())
    
    # Get filter parameters
    system_filter = request.args.get('system')
    search_query = request.args.get('q', '').strip()
    
    # Apply filters
    if system_filter:
        all_campaigns = [c for c in all_campaigns if c.system == system_filter]
    
    if search_query:
        search_lower = search_query.lower()
        all_campaigns = [c for c in all_campaigns 
                        if search_lower in c.name.lower() 
                        or (c.description and search_lower in c.description.lower())]
    
    # Get unique systems for filter bubbles
    all_systems = sorted(list({c.system for c in all_campaigns}))
    
    # Sort by next session date (for now, using creation date - we'll add session dates later)
    all_campaigns.sort(key=lambda x: x.created_at, reverse=True)
    
    return render_template('campaigns.html', 
                         campaigns=all_campaigns,
                         systems=all_systems,
                         current_system=system_filter,
                         search_query=search_query)

@app.route('/termine')
@login_required
def termine():
    # Collect all campaigns where user participates (DM or player)
    dm_campaigns = Campaign.query.filter_by(dm_id=current_user.id).all()
    player_campaigns = current_user.player_campaigns
    campaigns = list({c.id: c for c in dm_campaigns + player_campaigns}.values())

    if not campaigns:
        return render_template('termine.html', campaigns=[], sessions=[], polls=[], campaign_names={}, campaign_images={})

    campaign_ids = [c.id for c in campaigns]
    # Upcoming sessions (future only)
    sessions = (
        Session.query
        .filter(Session.campaign_id.in_(campaign_ids), Session.scheduled_at >= datetime.now())
        .order_by(Session.scheduled_at.asc())
        .all()
    )
    # Get all open polls across campaigns
    open_polls = (
        SessionPoll.query
        .filter(SessionPoll.campaign_id.in_(campaign_ids), SessionPoll.is_closed == False)
        .options(
            db.joinedload(SessionPoll.options)
            .joinedload(SessionPollOption.votes)
            .load_only(SessionPollVote.user_id, SessionPollVote.option_id)
        )
        .order_by(SessionPoll.created_at.desc())
        .all()
    )
    
    # Filter out polls where user has voted on all options
    polls = []
    for poll in open_polls:
        # Count total options and options where user has voted
        total_options = len(poll.options)
        voted_options = sum(
            1 for option in poll.options 
            if any(vote.user_id == current_user.id for vote in option.votes)
        )
        # Only include polls where user hasn't voted on all options
        if voted_options < total_options:
            polls.append(poll)
    # Build RSVP map for current user to avoid lazy-loading issues in templates
    session_ids = [s.id for s in sessions]
    resp_map = {}
    if session_ids:
        user_responses = (
            SessionResponse.query
            .filter(SessionResponse.session_id.in_(session_ids), SessionResponse.user_id == current_user.id)
            .all()
        )
        resp_map = {r.session_id: r.response for r in user_responses}

    campaign_names = {c.id: c.name for c in campaigns}
    campaign_images = {c.id: c.image for c in campaigns}
    return render_template('termine.html', campaigns=campaigns, sessions=sessions, polls=polls, campaign_names=campaign_names, campaign_images=campaign_images, resp_map=resp_map)

@app.route('/campaign/<int:campaign_id>')
@login_required
def view_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Check if user has access to this campaign
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, diese Kampagne anzusehen.', 'danger')
        return redirect(url_for('home'))
        
    # Get all characters for this campaign
    characters = Character.query.filter_by(campaign_id=campaign_id).all()
    
    # Get all NPCs for this campaign
    npcs = NPC.query.filter_by(campaign_id=campaign_id).order_by(NPC.name).all()
    
    # Get all quests for this campaign
    quests = Quest.query.filter_by(campaign_id=campaign_id).order_by(Quest.status, Quest.priority).all()
    
    # Get all sessions for this campaign (future and past)
    now = datetime.utcnow()
    upcoming_sessions = Session.query.filter(
        Session.campaign_id == campaign_id,
        Session.scheduled_at >= now
    ).order_by(Session.scheduled_at.asc()).all()
    
    past_sessions = Session.query.filter(
        Session.campaign_id == campaign_id,
        Session.scheduled_at < now
    ).order_by(Session.scheduled_at.desc()).limit(5).all()
    
    # Get all polls for this campaign
    polls = SessionPoll.query.filter_by(campaign_id=campaign_id, is_closed=False).all()
    
    # Create resp_map for RSVPs in this campaign
    resp_map = {}
    if upcoming_sessions:
        session_ids = [s.id for s in upcoming_sessions]
        user_responses = (
            SessionResponse.query
            .filter(SessionResponse.session_id.in_(session_ids), 
                   SessionResponse.user_id == current_user.id)
            .all()
        )
        resp_map = {r.session_id: r.response for r in user_responses}
    
    # Count pending actions for this campaign
    pending_actions = 0
    
    # Count open RSVPs for this campaign (sessions without user response)
    open_rsvps = sum(1 for s in upcoming_sessions if s.id not in resp_map)
    pending_actions += open_rsvps
    
    # Count open polls for this campaign where user hasn't voted
    open_polls = SessionPoll.query.filter(
        SessionPoll.campaign_id == campaign_id,
        SessionPoll.is_closed == False,
        ~SessionPoll.options.any(
            SessionPollOption.votes.any(user_id=current_user.id)
        )
    ).count()
    pending_actions += open_polls
    
    is_dm = (current_user.id == campaign.dm_id)
    
    return render_template('view_campaign.html', 
                         campaign=campaign, 
                         characters=characters,
                         npcs=npcs,
                         quests=quests,
                         sessions=upcoming_sessions,
                         past_sessions=past_sessions,
                         polls=polls,
                         is_dm=is_dm,
                         now=now,
                         resp_map=resp_map,
                         pending_actions_count=pending_actions)

@app.route('/campaign/<int:campaign_id>/sessions/new', methods=['GET', 'POST'])
@login_required
def plan_session(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if current_user.id != campaign.dm_id:
        flash('Nur der Spielleiter kann Sitzungen planen.', 'danger')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    if request.method == 'POST':
        title = request.form.get('title', '').strip() or None
        date_str = request.form.get('date', '').strip()
        time_str = request.form.get('time', '').strip()
        location = request.form.get('location', '').strip() or None
        notes = request.form.get('notes', '').strip() or None

        if not date_str or not time_str:
            flash('Datum und Uhrzeit sind erforderlich.', 'danger')
            return redirect(url_for('plan_session', campaign_id=campaign_id))

        try:
            scheduled_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash('Ungültiges Datum oder Uhrzeitformat.', 'danger')
            return redirect(url_for('plan_session', campaign_id=campaign_id))

        sess = Session(
            campaign_id=campaign.id,
            title=title,
            scheduled_at=scheduled_at,
            location=location,
            notes=notes,
            created_by=current_user.id
        )
        db.session.add(sess)
        db.session.commit()
        flash('Sitzung wurde geplant.', 'success')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    is_dm = True
    return render_template('plan_session.html', campaign=campaign, is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/sessions/<int:session_id>/rsvp', methods=['POST'])
@login_required
def rsvp_session(campaign_id, session_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung für diese Kampagne.', 'danger')
        return redirect(url_for('home'))

    sess = Session.query.filter_by(id=session_id, campaign_id=campaign.id).first_or_404()
    choice = (request.form.get('response') or '').strip().lower()
    if choice not in {'yes', 'no', 'maybe'}:
        flash('Ungültige Auswahl.', 'danger')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    resp = SessionResponse.query.filter_by(session_id=sess.id, user_id=current_user.id).first()
    if resp:
        resp.response = choice
        resp.updated_at = datetime.utcnow()
    else:
        resp = SessionResponse(session_id=sess.id, user_id=current_user.id, response=choice)
        db.session.add(resp)
    db.session.commit()
    # AJAX support
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Build updated summary
        yes, maybe, no = [], [], []
        for r in sess.responses:
            name = (r.user.full_name or r.user.username)
            if r.response == 'yes':
                yes.append(name)
            elif r.response == 'maybe':
                maybe.append(name)
            elif r.response == 'no':
                no.append(name)
        return jsonify({
            'ok': True,
            'session_id': sess.id,
            'my_response': choice,
            'yes': yes,
            'maybe': maybe,
            'no': no,
        })
    flash('Teilnahmestatus aktualisiert.', 'success')
    return redirect(url_for('view_campaign', campaign_id=campaign_id, focus=f"session-{session_id}"))

@app.route('/campaign/<int:campaign_id>/polls/new', methods=['GET', 'POST'])
@login_required
def new_poll(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if current_user.id != campaign.dm_id:
        flash('Nur der Spielleiter kann Termin-Umfragen erstellen.', 'danger')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip() or 'Termin-Umfrage'
        notes = (request.form.get('notes') or '').strip() or None

        # Collect up to 5 options from the form
        options = []
        for i in range(1, 6):
            date_str = (request.form.get(f'date_{i}') or '').strip()
            time_str = (request.form.get(f'time_{i}') or '').strip()
            location = (request.form.get(f'location_{i}') or '').strip() or None
            opt_notes = (request.form.get(f'notes_{i}') or '').strip() or None
            if date_str and time_str:
                try:
                    scheduled_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                except ValueError:
                    flash(f'Option {i}: Ungültiges Datum/Uhrzeit.', 'danger')
                    return redirect(url_for('new_poll', campaign_id=campaign_id))
                options.append((scheduled_at, location, opt_notes))

        if not options:
            flash('Bitte mindestens eine gültige Termin-Option angeben.', 'danger')
            return redirect(url_for('new_poll', campaign_id=campaign_id))

        poll = SessionPoll(campaign_id=campaign.id, title=title, notes=notes, created_by=current_user.id)
        db.session.add(poll)
        db.session.flush()
        for scheduled_at, location, opt_notes in options:
            db.session.add(SessionPollOption(poll_id=poll.id, scheduled_at=scheduled_at, location=location, notes=opt_notes))
        db.session.commit()
        flash('Termin-Umfrage erstellt.', 'success')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    return render_template('new_poll.html', campaign=campaign)

@app.route('/campaign/<int:campaign_id>/polls/<int:poll_id>/vote', methods=['POST'])
@login_required
def vote_poll_option(campaign_id, poll_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if not campaign.has_access(current_user):
        flash('Keine Berechtigung.', 'danger')
        return redirect(url_for('home'))

    poll = SessionPoll.query.filter_by(id=poll_id, campaign_id=campaign.id).first_or_404()
    if poll.is_closed:
        flash('Diese Umfrage ist bereits geschlossen.', 'warning')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    option_id = int(request.form.get('option_id') or 0)
    response = (request.form.get('response') or '').strip().lower()
    if response not in {'yes', 'no', 'maybe'}:
        flash('Ungültige Auswahl.', 'danger')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    option = SessionPollOption.query.filter_by(id=option_id, poll_id=poll.id).first_or_404()
    vote = SessionPollVote.query.filter_by(option_id=option.id, user_id=current_user.id).first()
    if vote:
        vote.response = response
        vote.updated_at = datetime.utcnow()
    else:
        vote = SessionPollVote(option_id=option.id, user_id=current_user.id, response=response)
        db.session.add(vote)
    db.session.commit()
    # AJAX support
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Summarize current votes for this option
        yes, maybe, no = [], [], []
        for v in option.votes:
            name = (v.user.full_name or v.user.username)
            if v.response == 'yes':
                yes.append(name)
            elif v.response == 'maybe':
                maybe.append(name)
            elif v.response == 'no':
                no.append(name)
        return jsonify({
            'ok': True,
            'poll_id': poll.id,
            'option_id': option.id,
            'my_response': response,
            'yes': yes,
            'maybe': maybe,
            'no': no,
        })
    flash('Abstimmung gespeichert.', 'success')
    return redirect(url_for('view_campaign', campaign_id=campaign_id, focus=f"poll-{poll_id}"))

@app.route('/campaign/<int:campaign_id>/polls/<int:poll_id>/finalize', methods=['POST'])
@login_required
def finalize_poll(campaign_id, poll_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if current_user.id != campaign.dm_id:
        flash('Nur der Spielleiter kann die Umfrage abschließen.', 'danger')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    poll = SessionPoll.query.filter_by(id=poll_id, campaign_id=campaign.id).first_or_404()
    if poll.is_closed:
        flash('Diese Umfrage ist bereits geschlossen.', 'warning')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    option_id = int(request.form.get('option_id') or 0)
    option = SessionPollOption.query.filter_by(id=option_id, poll_id=poll.id).first_or_404()

    # Create a real session from the chosen option
    sess = Session(
        campaign_id=campaign.id,
        title=poll.title or 'Geplante Sitzung',
        scheduled_at=option.scheduled_at,
        location=option.location,
        notes=poll.notes or option.notes,
        created_by=current_user.id,
    )
    db.session.add(sess)
    # Close the poll
    poll.is_closed = True
    db.session.commit()
    flash('Umfrage abgeschlossen und Sitzung erstellt.', 'success')
    return redirect(url_for('view_campaign', campaign_id=campaign_id, focus=f"session-{sess.id}"))

# Ensure sessions table exists without full migrations
with app.app_context():
    try:
        Session.__table__.create(bind=db.engine, checkfirst=True)
    except Exception:
        pass
    try:
        SessionResponse.__table__.create(bind=db.engine, checkfirst=True)
    except Exception:
        pass
    # Create poll tables if missing
    try:
        SessionPoll.__table__.create(bind=db.engine, checkfirst=True)
    except Exception:
        pass
    try:
        SessionPollOption.__table__.create(bind=db.engine, checkfirst=True)
    except Exception:
        pass
    try:
        SessionPollVote.__table__.create(bind=db.engine, checkfirst=True)
    except Exception:
        pass

@app.route('/campaign/<int:campaign_id>/sessions/<int:session_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_session(campaign_id, session_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if current_user.id != campaign.dm_id:
        flash('Nur der Spielleiter kann Sitzungen bearbeiten.', 'danger')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    sess = Session.query.filter_by(id=session_id, campaign_id=campaign.id).first_or_404()

    if request.method == 'POST':
        title = request.form.get('title', '').strip() or None
        date_str = request.form.get('date', '').strip()
        time_str = request.form.get('time', '').strip()
        location = request.form.get('location', '').strip() or None
        notes = request.form.get('notes', '').strip() or None

        if not date_str or not time_str:
            flash('Datum und Uhrzeit sind erforderlich.', 'danger')
            return redirect(url_for('edit_session', campaign_id=campaign_id, session_id=session_id))

        try:
            scheduled_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash('Ungültiges Datum oder Uhrzeitformat.', 'danger')
            return redirect(url_for('edit_session', campaign_id=campaign_id, session_id=session_id))

        sess.title = title
        sess.scheduled_at = scheduled_at
        sess.location = location
        sess.notes = notes
        db.session.commit()
        flash('Sitzung wurde aktualisiert.', 'success')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    # Pre-fill values for form
    is_dm = True
    return render_template('edit_session.html', campaign=campaign, sess=sess, is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/sessions/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(campaign_id, session_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if current_user.id != campaign.dm_id:
        flash('Nur der Spielleiter kann Sitzungen löschen.', 'danger')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))

    sess = Session.query.filter_by(id=session_id, campaign_id=campaign.id).first_or_404()
    db.session.delete(sess)
    db.session.commit()
    flash('Sitzung wurde gelöscht.', 'success')
    return redirect(url_for('view_campaign', campaign_id=campaign_id))

@app.route('/campaign/<int:campaign_id>/quests')
@login_required
def quests(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, diese Kampagne anzusehen.', 'danger')
        return redirect(url_for('home'))

    q = request.args.get('q', '').strip()
    status = request.args.get('status', 'open')
    # only allow 'open' or 'done' as status filters
    if status not in ('open', 'done', ''):
        status = 'open'
    main_only = str(request.args.get('main', '')).lower() in ('1','true','on')

    query = Quest.query.filter_by(campaign_id=campaign.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Quest.title.ilike(like), Quest.description.ilike(like), Quest.tags.ilike(like)))
    if status:
        # normalize legacy values by trimming and lowercasing in DB filter
        query = query.filter(func.lower(func.trim(Quest.status)) == status)
    if main_only:
        query = query.filter_by(is_main=True)

    quests = query.order_by(Quest.is_main.desc(), Quest.priority.desc(), Quest.created_at.desc()).all()
    is_dm = current_user.id == campaign.dm_id
    return render_template('quests.html', campaign=campaign, quests=quests, q=q, status=status, main_only=main_only, is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/quests/new', methods=['GET', 'POST'])
@login_required
def new_quest(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, diese Kampagne anzusehen.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        reward = request.form.get('reward', '').strip()
        status = request.form.get('status', 'open')
        # normalize status: only 'open' or 'done'
        if status not in ('open', 'done'):
            status = 'open'
        priority = request.form.get('priority', 'normal')
        is_main = bool(request.form.get('is_main'))
        tags = request.form.get('tags', '').strip()

        if not title:
            flash('Ein Quest-Titel ist erforderlich.', 'danger')
            return redirect(url_for('new_quest', campaign_id=campaign.id))

        quest = Quest(
            title=title,
            description=description,
            reward=reward,
            status=status,
            priority=priority,
            is_main=is_main,
            tags=tags,
            campaign_id=campaign.id,
            created_by=current_user.id
        )
        db.session.add(quest)
        db.session.commit()
        flash('Quest erstellt.', 'success')
        return redirect(url_for('quests', campaign_id=campaign.id))

    is_dm = current_user.id == campaign.dm_id
    return render_template('new_quest.html', campaign=campaign, is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/quests/<int:quest_id>')
@login_required
def view_quest(campaign_id, quest_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, diese Kampagne anzusehen.', 'danger')
        return redirect(url_for('home'))

    quest = Quest.query.filter_by(id=quest_id, campaign_id=campaign.id).first_or_404()
    is_dm = current_user.id == campaign.dm_id
    return render_template('view_quest.html', campaign=campaign, quest=quest, is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/quests/<int:quest_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quest(campaign_id, quest_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, diese Kampagne anzusehen.', 'danger')
        return redirect(url_for('home'))

    quest = Quest.query.filter_by(id=quest_id, campaign_id=campaign.id).first_or_404()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        reward = request.form.get('reward', '').strip()
        status = request.form.get('status', 'open')
        if status not in ('open', 'done'):
            status = 'open'
        priority = request.form.get('priority', 'normal')
        is_main = bool(request.form.get('is_main'))
        tags = request.form.get('tags', '').strip()

        if not title:
            flash('Ein Quest-Titel ist erforderlich.', 'danger')
            return redirect(url_for('edit_quest', campaign_id=campaign.id, quest_id=quest.id))

        quest.title = title
        quest.description = description
        quest.reward = reward
        quest.status = status
        quest.priority = priority
        quest.is_main = is_main
        quest.tags = tags
        db.session.commit()
        flash('Quest aktualisiert.', 'success')
        return redirect(url_for('view_quest', campaign_id=campaign.id, quest_id=quest.id))

    # GET: render edit form
    is_dm = current_user.id == campaign.dm_id
    return render_template('edit_quest.html', campaign=campaign, quest=quest, is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/quests/<int:quest_id>/update_tags', methods=['POST'])
@login_required
def update_quest_tags(campaign_id, quest_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if not campaign.has_access(current_user):
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    quest = Quest.query.filter_by(id=quest_id, campaign_id=campaign.id).first_or_404()
    # Only DM or creator can edit tags
    if current_user.id not in (campaign.dm_id, quest.created_by):
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    data = request.get_json(silent=True) or {}
    tags = data.get('tags', [])
    # Support string input too
    if isinstance(tags, str):
        parts = [p.strip() for p in tags.split(',') if p.strip()]
    else:
        parts = [str(p).strip() for p in (tags or []) if str(p).strip()]
    # De-duplicate case-insensitively preserving order
    seen = set()
    normed = []
    for p in parts:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            normed.append(p)
    quest.tags = ', '.join(normed)
    db.session.commit()
    return jsonify({'success': True, 'tags': quest.tags})

@app.route('/campaign/<int:campaign_id>/quests/<int:quest_id>/status', methods=['POST'])
@login_required
def update_quest_status(campaign_id, quest_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, diese Kampagne anzusehen.', 'danger')
        return redirect(url_for('home'))

    quest = Quest.query.filter_by(id=quest_id, campaign_id=campaign.id).first_or_404()
    new_status = request.form.get('status', '')
    if new_status in ('open', 'done'):
        quest.status = new_status
        db.session.commit()
        flash('Status aktualisiert.', 'success')
    else:
        flash('Ungültiger Status.', 'danger')

    # Redirect back to quest detail
    return redirect(url_for('view_quest', campaign_id=campaign.id, quest_id=quest.id))

@app.route('/campaign/<int:campaign_id>/players', methods=['GET', 'POST'])
@login_required
def manage_players(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Check if user is the DM of this campaign
    if current_user.id != campaign.dm_id:
        flash('Nur der Spielleiter kann Spieler verwalten.', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        # Handle player invitation
        user_id = request.form.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user and user != current_user:
                if user in campaign.players:
                    flash(f'{user.username} ist bereits ein Spieler in dieser Kampagne.', 'warning')
                else:
                    campaign.players.append(user)
                    db.session.commit()
                    flash(f'{user.username} wurde zur Kampagne hinzugefügt.', 'success')
            else:
                flash('Benutzer nicht gefunden oder ungültig.', 'danger')
        return redirect(url_for('manage_players', campaign_id=campaign_id))
    
    # Get all users except the DM
    all_users = User.query.filter(User.id != campaign.dm_id).all()
    
    is_dm = True  # by definition in this view
    return render_template(
        'manage_players.html',
        campaign=campaign,
        all_users=all_users,
        is_dm=is_dm
    )

@app.route('/campaign/<int:campaign_id>/remove_player/<int:user_id>', methods=['POST'])
@login_required
def remove_player(campaign_id, user_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Check if user is the DM of this campaign
    if current_user.id != campaign.dm_id:
        flash('Nur der Spielleiter kann Spieler entfernen.', 'danger')
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    if user in campaign.players:
        campaign.players.remove(user)
        db.session.commit()
        flash(f'{user.username} wurde aus der Kampagne entfernt.', 'success')
    
    return redirect(url_for('manage_players', campaign_id=campaign_id))

@app.route('/campaign/<int:campaign_id>/chat')
@login_required
def chat(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if not campaign.has_access(current_user):
        abort(403)
    
    is_dm = current_user.id == campaign.dm_id
    return render_template('chat.html', campaign=campaign, is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/character', methods=['GET', 'POST'])
@login_required
def manage_character(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Check if user has access to this campaign
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, auf diese Kampagne zuzugreifen.', 'danger')
        return redirect(url_for('home'))
    
    # Get or create character for this user in this campaign
    character = campaign.get_character_for_user(current_user.id)
    
    if request.method == 'POST':
        # Handle form submission
        character_name = request.form.get('character_name', '').strip()
        character_class = request.form.get('character_class', '').strip()
        level = request.form.get('level', type=int)
        race = request.form.get('race', '').strip()
        description = request.form.get('description', '').strip()
        
        # Validate required fields
        if not character_name:
            flash('Ein Charaktername ist erforderlich.', 'danger')
            return redirect(url_for('manage_character', campaign_id=campaign_id))
        
        # Handle file upload
        image_filename = None
        if 'character_image' in request.files:
            file = request.files['character_image']
            if file and file.filename and allowed_file(file.filename):
                # Delete old image if exists
                if character and character.image and character.image != 'default_character.jpg':
                    try:
                        os.remove(os.path.join(app.config['CHARACTER_IMAGES'], character.image))
                    except OSError:
                        pass
                
                # Save new image
                filename = secure_filename(file.filename)
                # Add random string to make filename unique
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file.save(os.path.join(app.config['CHARACTER_IMAGES'], unique_filename))
                image_filename = unique_filename
        
        # Create or update character
        if not character:
            character = Character(
                user_id=current_user.id,
                campaign_id=campaign.id,
                character_name=character_name,
                display_name=character_name,  # Set display_name same as character_name by default
                character_class=character_class,
                level=level,
                race=race,
                description=description,
                image=image_filename or 'default_character.jpg'
            )
            db.session.add(character)
        else:
            character.character_name = character_name
            character.display_name = character_name  # Update display_name when character_name changes
            character.character_class = character_class
            character.level = level
            character.race = race
            character.description = description
            if image_filename:
                character.image = image_filename
        
        db.session.commit()
        flash('Charakter erfolgreich gespeichert!', 'success')
        return redirect(url_for('view_campaign', campaign_id=campaign_id))
    
    is_dm = current_user.id == campaign.dm_id
    return render_template('character.html', campaign=campaign, character=character, is_dm=is_dm)

# Route to serve character images
@app.route('/character_images/<filename>')
def character_image(filename):
    return send_from_directory(app.config['CHARACTER_IMAGES'], filename)

# Chat routes
@app.route('/campaign/<int:campaign_id>/chat/messages')
@login_required
def get_chat_messages(campaign_id):
    try:
        # Get the campaign and verify access
        campaign = Campaign.query.get_or_404(campaign_id)
        if not campaign.has_access(current_user):
            print(f"Access denied: User {current_user.id} doesn't have access to campaign {campaign_id}")
            abort(403)
        
        print(f"Fetching messages for campaign {campaign_id}")
        
        # Get last 50 messages for this campaign only
        messages = Message.query.filter_by(campaign_id=campaign_id)\
                              .order_by(Message.timestamp.desc())\
                              .limit(50)\
                              .all()
        
        print(f"Found {len(messages)} messages for campaign {campaign_id}")
        
        # Convert messages to dict for JSON response
        messages_data = []
        for msg in reversed(messages):  # Oldest first
            is_dm = msg.user_id == campaign.dm_id
            sender_name = "DM" if is_dm else (msg.character.character_name if msg.character and hasattr(msg.character, 'character_name') else msg.user.username)
            
            message_data = {
                'id': msg.id,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'sender_name': sender_name,
                'is_dm': is_dm,
                'character_image': get_character_image_url(msg.character, is_dm)
            }
            messages_data.append(message_data)
        
        print(f"Returning {len(messages_data)} messages for campaign {campaign_id}")
        return jsonify(messages_data)
        
    except Exception as e:
        print(f"Error in get_chat_messages for campaign {campaign_id}:")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

def get_character_image_url(character, is_dm):
    """Helper function to get the appropriate image URL for a character"""
    if is_dm:
        # Return a Font Awesome dice icon for DM
        return 'fas fa-dice-d20 fa-2x'
    
    if not character or not hasattr(character, 'image') or not character.image or character.image == 'default_character.jpg':
        return 'fas fa-user-circle fa-2x'  # Default user icon
        
    return url_for('static', filename=f'character_images/{character.image}', _external=True)

def log_error(message, error=None):
    """Helper function to log errors consistently"""
    print(f"\n!!! ERROR: {message}")
    if error:
        print(f"Error type: {type(error).__name__}")
        print(f"Error details: {str(error)}")
        import traceback
        traceback.print_exc()

@app.route('/campaign/<int:campaign_id>/chat/send', methods=['POST'])
@login_required
def send_chat_message(campaign_id):
    print("\n=== SEND MESSAGE REQUEST ===")
    print(f"User: {current_user.id} ({current_user.username})")
    print(f"Campaign ID: {campaign_id}")
    print(f"Request form data: {request.form}")
    
    try:
        
        campaign = Campaign.query.get_or_404(campaign_id)
        if not campaign.has_access(current_user):
            print("Access denied: User doesn't have access to this campaign")
            abort(403)
        
        content = request.form.get('content', '').strip()
        print(f"Content: {content}")
        
        if not content:
            print("Error: Empty content")
            return jsonify({'error': 'Message content is required', 'success': False}), 400
        
        # Get character for this user in campaign
        try:
            character = campaign.get_character_for_user(current_user.id)
            print(f"Found character: {character.character_name if character else 'None'}")
            
            # Debug: Print character details
            if character:
                print(f"Character ID: {character.id}, Name: {character.character_name}, Image: {getattr(character, 'image', 'N/A')}")
            else:
                print("No character found for this user in the campaign")
        except Exception as e:
            log_error("Error getting character for user", e)
            return jsonify({
                'success': False,
                'error': 'Error getting character information',
                'details': str(e)
            }), 500
        
        # Create new message
        try:
            message = Message(
                content=content,
                campaign_id=campaign_id,
                user_id=current_user.id,
                character_id=character.id if character else None
            )
            
            db.session.add(message)
            db.session.commit()
            print(f"Message created with ID: {message.id}")
        except Exception as e:
            db.session.rollback()
            log_error("Error saving message to database", e)
            return jsonify({
                'success': False,
                'error': 'Error saving message',
                'details': str(e)
            }), 500
        print(f"Message saved with ID: {message.id}")
        
        # Prepare response data
        is_dm = current_user.id == campaign.dm_id
        response_data = {
            'success': True,
            'message_id': message.id,
            'timestamp': message.timestamp.isoformat(),
            'sender_name': 'DM' if is_dm else (character.character_name if character else current_user.username),
            'is_dm': is_dm,
            'content': content
        }
        
        # Add character image URL using the helper function
        response_data['character_image'] = get_character_image_url(character, is_dm)
        
        print("Sending response:", response_data)
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in send_chat_message: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

# NPC Management Routes
@app.route('/campaign/<int:campaign_id>/npcs')
@login_required
def npcs(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Check if user has access to this campaign (DM or player)
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, diese Kampagne zu sehen.', 'danger')
        return redirect(url_for('campaigns'))
    
    # Get search query
    search_query = request.args.get('search', '')
    # Important toggle
    important_param = request.args.get('important')
    important_only = str(important_param).lower() in ('1', 'true', 'on')
    
    # Get NPCs for this campaign
    npcs_query = NPC.query.filter_by(campaign_id=campaign_id)
    
    # Apply search filter if provided
    if search_query:
        search = f"%{search_query}%"
        filters = [
            NPC.name.ilike(search),
            NPC.race.ilike(search),
            NPC.notes.ilike(search),
            NPC.gender.ilike(search),
            NPC.tags.ilike(search)
        ]
        # If numeric search, also match age exactly
        if search_query.isdigit():
            try:
                filters.append(NPC.age == int(search_query))
            except ValueError:
                pass
        npcs_query = npcs_query.filter(or_(*filters))
    
    # Apply important-only filter if toggle is active
    if important_only:
        npcs_query = npcs_query.filter(NPC.is_important.is_(True))
    
    npcs = npcs_query.order_by(NPC.name).all()
    
    is_dm = current_user.id == campaign.dm_id
    return render_template('npcs.html', 
                         campaign=campaign, 
                         npcs=npcs, 
                         search_query=search_query,
                         important_only=important_only,
                         title='NPCs',
                         is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/npc/<int:npc_id>')
@login_required
def view_npc(campaign_id, npc_id):
    npc = NPC.query.get_or_404(npc_id)
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Check if user has access to this campaign (DM or player)
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, diesen NPC zu sehen.', 'danger')
        return redirect(url_for('campaigns'))
    
    is_dm = current_user.id == campaign.dm_id
    return render_template('view_npc.html', 
                         campaign=campaign, 
                         npc=npc,
                         title=npc.name,
                         is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/npc/new', methods=['GET', 'POST'])
@login_required
def new_npc(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Allow both DM and players to create NPCs
    if not campaign.has_access(current_user):
        flash('Du hast keine Berechtigung, in dieser Kampagne NPCs zu erstellen.', 'danger')
        return redirect(url_for('campaigns'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            if not name:
                flash('Bitte gib einen Namen für den NPC ein.', 'danger')
                is_dm = (current_user.id == campaign.dm_id)
                return render_template('edit_npc.html', campaign=campaign, npc=None, title='Neuer NPC', is_dm=is_dm)
            
            npc = NPC(
                name=name,
                race=request.form.get('race') or None,
                age=int(request.form.get('age')) if request.form.get('age') else None,
                gender=request.form.get('gender') or None,
                appearance=request.form.get('appearance') or None,
                personality=request.form.get('personality') or None,
                background=request.form.get('background') or None,
                notes=request.form.get('notes') or None,
                tags=(request.form.get('tags') or '').strip() or None,
                is_important=('is_important' in request.form),
                campaign_id=campaign.id,
                created_by=current_user.id
            )
            
            # Handle image upload
            if 'image' in request.files and request.files['image'].filename != '':
                file = request.files['image']
                if file and allowed_file(file.filename):
                    # Ensure directory exists
                    os.makedirs(os.path.join(app.root_path, 'static/npc_images'), exist_ok=True)
                    filename = secure_filename(f"{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}")
                    file.save(os.path.join(app.root_path, 'static/npc_images', filename))
                    npc.image = filename
            
            db.session.add(npc)
            db.session.commit()
            flash('NPC erfolgreich erstellt!', 'success')
            return redirect(url_for('view_npc', campaign_id=campaign_id, npc_id=npc.id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error creating NPC: {str(e)}')
            flash('Fehler beim Erstellen des NPCs. Bitte versuche es erneut.', 'danger')
    
    is_dm = (current_user.id == campaign.dm_id)
    return render_template('edit_npc.html', campaign=campaign, npc=None, title='Neuer NPC', is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/npc/<int:npc_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_npc(campaign_id, npc_id):
    npc = NPC.query.get_or_404(npc_id)
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # DM can edit all; players can edit NPCs they created
    if not (current_user.id == campaign.dm_id or npc.created_by == current_user.id):
        flash('Du darfst diesen NPC nicht bearbeiten.', 'danger')
        return redirect(url_for('view_npc', campaign_id=campaign_id, npc_id=npc_id))
    
    if request.method == 'POST':
        try:
            npc.name = request.form.get('name', npc.name)
            npc.race = request.form.get('race', npc.race)
            npc.age = request.form.get('age', npc.age)
            npc.gender = request.form.get('gender', npc.gender)
            npc.appearance = request.form.get('appearance', npc.appearance)
            npc.personality = request.form.get('personality', npc.personality)
            npc.background = request.form.get('background', npc.background)
            npc.notes = request.form.get('notes', npc.notes)
            npc.tags = (request.form.get('tags') or '').strip() or None
            npc.is_important = ('is_important' in request.form)
            
            # Handle file upload if a new image is provided
            if 'image' in request.files and request.files['image'].filename != '':
                file = request.files['image']
                if file and allowed_file(file.filename):
                    # Delete old image if it's not the default
                    if npc.image != 'default_npc.jpg':
                        try:
                            os.remove(os.path.join(app.root_path, 'static/npc_images', npc.image))
                        except:
                            pass
                    
                    # Save new image
                    filename = secure_filename(f"{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}")
                    file.save(os.path.join(app.root_path, 'static/npc_images', filename))
                    npc.image = filename
            
            # Handle image removal if requested
            if 'remove_image' in request.form and request.form['remove_image'] == 'on':
                if npc.image != 'default_npc.jpg':
                    try:
                        os.remove(os.path.join(app.root_path, 'static/npc_images', npc.image))
                    except:
                        pass
                    npc.image = 'default_npc.jpg'
            
            db.session.commit()
            flash('NPC erfolgreich aktualisiert!', 'success')
            return redirect(url_for('view_npc', campaign_id=campaign_id, npc_id=npc_id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error updating NPC: {str(e)}')
            flash('Fehler beim Aktualisieren des NPCs. Bitte versuche es erneut.', 'danger')
    
    is_dm = (current_user.id == campaign.dm_id)
    return render_template('edit_npc.html', 
                         campaign=campaign, 
                         npc=npc,
                         title=f'Bearbeite {npc.name}',
                         is_dm=is_dm)

@app.route('/campaign/<int:campaign_id>/npc/<int:npc_id>/update_notes', methods=['POST'])
@login_required
def update_npc_notes(campaign_id, npc_id):
    npc = NPC.query.get_or_404(npc_id)
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Check if user has access to this campaign (DM or player)
    if not campaign.has_access(current_user):
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403
    
    try:
        notes = request.json.get('notes', '')
        npc.notes = notes
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error updating NPC notes: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/campaign/<int:campaign_id>/npc/<int:npc_id>/update_appearance', methods=['POST'])
@login_required
def update_npc_appearance(campaign_id, npc_id):
    npc = NPC.query.get_or_404(npc_id)
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Only DM or NPC creator can edit appearance
    if not (current_user.id == campaign.dm_id or npc.created_by == current_user.id):
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403
    
    try:
        appearance = request.json.get('appearance', '')
        npc.appearance = appearance
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error updating NPC appearance: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/campaign/<int:campaign_id>/npc/<int:npc_id>/update_personality', methods=['POST'])
@login_required
def update_npc_personality(campaign_id, npc_id):
    npc = NPC.query.get_or_404(npc_id)
    campaign = Campaign.query.get_or_404(campaign_id)

    if not (current_user.id == campaign.dm_id or npc.created_by == current_user.id):
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    try:
        personality = request.json.get('personality', '')
        npc.personality = personality
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error updating NPC personality: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/campaign/<int:campaign_id>/npc/<int:npc_id>/update_background', methods=['POST'])
@login_required
def update_npc_background(campaign_id, npc_id):
    npc = NPC.query.get_or_404(npc_id)
    campaign = Campaign.query.get_or_404(campaign_id)

    if not (current_user.id == campaign.dm_id or npc.created_by == current_user.id):
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    try:
        background = request.json.get('background', '')
        npc.background = background
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error updating NPC background: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/campaign/<int:campaign_id>/npc/<int:npc_id>/update_tags', methods=['POST'])
@login_required
def update_npc_tags(campaign_id, npc_id):
    npc = NPC.query.get_or_404(npc_id)
    campaign = Campaign.query.get_or_404(campaign_id)

    # Only DM or NPC creator can edit tags
    if not (current_user.id == campaign.dm_id or npc.created_by == current_user.id):
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    try:
        # Expect a list of tags or a comma-separated string
        data = request.get_json(silent=True) or {}
        tags = data.get('tags', '')
        if isinstance(tags, list):
            # Normalize: trim, remove empties, deduplicate preserving order
            seen = set()
            normalized = []
            for t in tags:
                s = (t or '').strip()
                if s and s.lower() not in seen:
                    seen.add(s.lower())
                    normalized.append(s)
            npc.tags = ', '.join(normalized) if normalized else None
        else:
            # string path
            parts = [p.strip() for p in str(tags).split(',')]
            normalized = []
            seen = set()
            for p in parts:
                if p and p.lower() not in seen:
                    seen.add(p.lower())
                    normalized.append(p)
            npc.tags = ', '.join(normalized) if normalized else None

        db.session.commit()
        return jsonify({'success': True, 'tags': npc.tags or ''})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error updating NPC tags: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/campaign/<int:campaign_id>/npc/<int:npc_id>/delete', methods=['POST'])
@login_required
def delete_npc(campaign_id, npc_id):
    npc = NPC.query.get_or_404(npc_id)
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Only DM can delete NPCs
    if current_user.id != campaign.dm_id:
        flash('Nur der Spielleiter kann NPCs löschen.', 'danger')
        return redirect(url_for('view_npc', campaign_id=campaign_id, npc_id=npc_id))
    
    try:
        # Delete the NPC's image if it's not the default
        if npc.image != 'default_npc.jpg':
            try:
                os.remove(os.path.join(app.root_path, 'static/npc_images', npc.image))
            except:
                pass
        
        db.session.delete(npc)
        db.session.commit()
        flash('NPC erfolgreich gelöscht!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting NPC: {str(e)}')
        flash('Fehler beim Löschen des NPCs. Bitte versuche es erneut.', 'danger')
    
    return redirect(url_for('npcs', campaign_id=campaign_id))

# Route to serve NPC images
@app.route('/npc_images/<filename>')
def npc_image(filename):
    return send_from_directory('static/npc_images', filename)

@app.route('/dice')
@login_required
def dice():
    return render_template('dice.html', title='Würfeln')

@app.context_processor
def inject_pending_actions():
    if not current_user.is_authenticated:
        return {}
        
    # Get campaigns where user is DM or player
    dm_campaigns = Campaign.query.filter_by(dm_id=current_user.id).all()
    player_campaigns = current_user.player_campaigns
    campaigns = list({c.id: c for c in dm_campaigns + player_campaigns}.values())
    
    if not campaigns:
        return {'pending_actions_count': 0}
        
    campaign_ids = [c.id for c in campaigns]
    
    # Count open RSVPs (sessions without user response)
    open_rsvps = db.session.query(Session).filter(
        Session.campaign_id.in_(campaign_ids),
        Session.scheduled_at >= datetime.now(),
        ~Session.responses.any(user_id=current_user.id)
    ).count()
    
    # Count open polls where user hasn't voted
    open_polls = db.session.query(SessionPoll).filter(
        SessionPoll.campaign_id.in_(campaign_ids),
        SessionPoll.is_closed == False,
        ~SessionPoll.options.any(
            SessionPollOption.votes.any(user_id=current_user.id)
        )
    ).count()
    
    return {'pending_actions_count': open_rsvps + open_polls}

if __name__ == '__main__':
    with app.app_context():
        # Create necessary directories
        os.makedirs(os.path.join(app.root_path, 'static/campaign_images'), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, 'static/character_images'), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, 'static/images'), exist_ok=True)
        # Create database tables
        db.create_all()
    app.run(debug=True)
