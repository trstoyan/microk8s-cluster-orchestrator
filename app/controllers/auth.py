"""Authentication endpoints for the MicroK8s Cluster Orchestrator."""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from ..models.database import db
from ..models.flask_models import User

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember_me = 'remember_me' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
                return redirect(url_for('auth.login'))
            
            # Update login tracking
            user.last_login = datetime.utcnow()
            user.login_count += 1
            db.session.commit()
            
            login_user(user, remember=remember_me)
            
            # Redirect to the page user was trying to access or dashboard
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('web.dashboard')
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """User logout."""
    user_name = current_user.full_name
    logout_user()
    flash(f'Goodbye, {user_name}!', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))
    
    # Check if registration is allowed (only if no admin users exist)
    admin_count = User.query.filter_by(is_admin=True).count()
    if admin_count == 0:
        # First user becomes admin
        is_first_user = True
    else:
        # Check if current user is admin (for creating additional users)
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Registration is restricted. Please contact an administrator.', 'error')
            return redirect(url_for('auth.login'))
        is_first_user = False
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        
        if User.query.filter_by(username=username).first():
            errors.append('Username already exists.')
        
        if not email or '@' not in email:
            errors.append('Please provide a valid email address.')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email address already registered.')
        
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            # Create new user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_admin=is_first_user  # First user becomes admin
            )
            user.set_password(password)
            
            try:
                db.session.add(user)
                db.session.commit()
                
                if is_first_user:
                    flash(f'Admin account created successfully! Welcome, {user.full_name}!', 'success')
                    login_user(user)
                    return redirect(url_for('web.dashboard'))
                else:
                    flash(f'User account created successfully for {user.full_name}!', 'success')
                    return redirect(url_for('auth.login'))
                    
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating user: {str(e)}', 'error')
    
    return render_template('auth/register.html', is_first_user=admin_count == 0)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', '').strip()
        current_user.last_name = request.form.get('last_name', '').strip()
        current_user.email = request.form.get('email', '').strip()
        
        # Check if email is already taken by another user
        existing_user = User.query.filter_by(email=current_user.email).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Email address is already taken by another user.', 'error')
        else:
            try:
                db.session.commit()
                flash('Profile updated successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating profile: {str(e)}', 'error')
    
    return render_template('auth/profile.html')

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page."""
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
        elif len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'error')
        else:
            current_user.set_password(new_password)
            try:
                db.session.commit()
                flash('Password changed successfully!', 'success')
                return redirect(url_for('auth.profile'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error changing password: {str(e)}', 'error')
    
    return render_template('auth/change_password.html')

@bp.route('/users')
@login_required
def users():
    """User management page (admin only)."""
    if not current_user.is_admin:
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('web.dashboard'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/users.html', users=users)

@bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
def toggle_user_admin(user_id):
    """Toggle user admin status (admin only)."""
    if not current_user.is_admin:
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('web.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'error')
    else:
        user.is_admin = not user.is_admin
        try:
            db.session.commit()
            status = 'granted' if user.is_admin else 'revoked'
            flash(f'Admin privileges {status} for {user.full_name}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return redirect(url_for('auth.users'))

@bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
def toggle_user_active(user_id):
    """Toggle user active status (admin only)."""
    if not current_user.is_admin:
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('web.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
    else:
        user.is_active = not user.is_active
        try:
            db.session.commit()
            status = 'activated' if user.is_active else 'deactivated'
            flash(f'User {user.full_name} {status}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return redirect(url_for('auth.users'))

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user (admin only)."""
    if not current_user.is_admin:
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('web.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
    else:
        try:
            # Update operations to remove user reference
            from ..models.flask_models import Operation
            Operation.query.filter_by(user_id=user.id).update({'user_id': None})
            
            db.session.delete(user)
            db.session.commit()
            flash(f'User {user.full_name} deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('auth.users'))
