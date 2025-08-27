from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from .models import User, Campaign, Character, db
from .extensions import get_supabase
from datetime import datetime
import os

# Create main blueprint
main = Blueprint('main', __name__)

@main.route('/')
def home():
    if current_user.is_authenticated:
        # Get user's campaigns
        campaigns = current_user.dm_campaigns + current_user.player_campaigns
        return render_template('home.html', campaigns=campaigns)
    return render_template('landing.html')

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@main.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    try:
        current_user.full_name = request.form.get('full_name')
        current_user.bio = request.form.get('bio')
        current_user.profile_updated = True
        
        # Handle profile picture upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    filename = f"{current_user.id}_{int(datetime.utcnow().timestamp())}.{file.filename.rsplit('.', 1)[1].lower()}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Delete old profile picture if it's not the default
                    if current_user.profile_pic != 'default.jpg':
                        try:
                            old_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.profile_pic)
                            if os.path.exists(old_filepath):
                                os.remove(old_filepath)
                        except Exception as e:
                            current_app.logger.error(f"Error deleting old profile picture: {str(e)}")
                    
                    current_user.profile_pic = filename
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating profile: {str(e)}")
        flash('An error occurred while updating your profile.', 'danger')
    
    return redirect(url_for('main.profile'))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# Error handlers
@main.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@main.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@main.app_errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@main.app_errorhandler(401)
def unauthorized_error(error):
    return redirect(url_for('auth.login'))
