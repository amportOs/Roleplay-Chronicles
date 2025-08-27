from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from .models import User, db
from .extensions import get_supabase
from datetime import datetime
import os

# Create auth blueprint
auth = Blueprint('auth', __name__)

# Helper functions
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be an admin to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        if not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('auth.login'))
        
        try:
            supabase = get_supabase()
            response = supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if not response.user:
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Get or create user in our database
            user = User.get_or_create_from_supabase(response.user)
            
            if not user.is_approved and not user.is_admin:
                flash('Your account is pending approval by an administrator.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Log the user in
            login_user(user, remember=remember)
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash('Successfully logged in!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.home'))
            
        except Exception as e:
            error_message = str(e).lower()
            if 'email not confirmed' in error_message:
                flash('Please confirm your email before logging in.', 'warning')
            elif 'invalid login credentials' in error_message:
                flash('Invalid email or password.', 'danger')
            else:
                current_app.logger.error(f'Login error: {str(e)}')
                flash('An error occurred during login. Please try again.', 'danger')
            return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not all([email, password, confirm_password]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('auth.register'))
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))
        
        try:
            supabase = get_supabase()
            
            # Check if email already exists in our database
            if User.query.filter_by(email=email).first():
                flash('Email already registered. Please log in instead.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Create user in Supabase Auth
            response = supabase.auth.sign_up({
                'email': email,
                'password': password,
                'options': {
                    'data': {
                        'email_redirect_to': url_for('auth.login', _external=True)
                    }
                }
            })
            
            if not response.user:
                flash('Registration failed. Please try again.', 'danger')
                return redirect(url_for('auth.register'))
            
            # Create user in our database
            user = User(
                id=response.user.id,
                email=email,
                is_approved=False  # Admin needs to approve new users
            )
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please check your email to verify your account.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f'Registration error: {str(e)}')
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('auth.register'))
    
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
    except Exception as e:
        current_app.logger.error(f'Logout error: {str(e)}')
    
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Please enter your email address.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        try:
            supabase = get_supabase()
            supabase.auth.reset_password_email(
                email,
                {
                    'redirect_to': url_for('auth.reset_password', _external=True)
                }
            )
            flash('Password reset link has been sent to your email.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f'Password reset error: {str(e)}')
            flash('An error occurred while processing your request. Please try again.', 'danger')
            return redirect(url_for('auth.forgot_password'))
    
    return render_template('forgot_password.html')

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    token = request.args.get('token')
    
    if not token:
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or not confirm_password:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
        
        try:
            supabase = get_supabase()
            response = supabase.auth.update_user({
                'password': password
            })
            
            if not response.user:
                raise Exception('Failed to update password')
            
            flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f'Password reset error: {str(e)}')
            flash('An error occurred while resetting your password. The link may have expired.', 'danger')
            return redirect(url_for('auth.forgot_password'))
    
    return render_template('reset_password.html', token=token)
