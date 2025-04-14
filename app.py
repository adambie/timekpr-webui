from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
from datetime import datetime, date, timedelta
import json
import logging

from src.database import db, ManagedUser, UserTimeUsage, Settings
from src.ssh_helper import SSHClient
from src.task_manager import BackgroundTaskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timekpr.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

# Initialize background task manager
task_manager = BackgroundTaskManager()
task_manager.init_app(app)

# Admin username remains hardcoded
ADMIN_USERNAME = 'admin'

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Get the admin password from settings, default to 'admin'
        admin_password = Settings.get_value('admin_password', 'admin')
        
        if username == ADMIN_USERNAME and password == admin_password:
            session['logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'
            flash(error, 'danger')
    
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    # Get all valid users - make sure we're getting fresh data by expiring SQLAlchemy's cache
    db.session.expire_all()
    users = ManagedUser.query.filter_by(is_valid=True).all()
    
    # Track users with pending time adjustments
    pending_adjustments = {}
    
    # Prepare user data for the dashboard
    user_data = []
    for user in users:
        # Get usage data for charts
        usage_data = user.get_recent_usage(days=7)
        
        # Get time left today if available
        time_left = user.get_config_value('TIME_LEFT_DAY')
        if time_left is not None:
            time_left_hours = time_left // 3600
            time_left_minutes = (time_left % 3600) // 60
            time_left_formatted = f"{time_left_hours}h {time_left_minutes}m"
        else:
            time_left_formatted = "Unknown"
        
        # Do NOT format last_checked time - pass the datetime object directly
        # So the template can format it
        
        # Check for pending time adjustments
        if user.pending_time_adjustment is not None and user.pending_time_operation is not None:
            minutes = user.pending_time_adjustment // 60
            operation = user.pending_time_operation
            pending_adjustments[str(user.id)] = f"{operation}{minutes} minutes"
        
        user_data.append({
            'id': user.id,
            'username': user.username,
            'system_ip': user.system_ip,
            'last_checked': user.last_checked,  # Keep as datetime object
            'usage_data': usage_data,
            'time_left': time_left_formatted
        })
    
    return render_template('dashboard.html', users=user_data, pending_adjustments=pending_adjustments)

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    # Get all managed users
    users = ManagedUser.query.all()
    return render_template('admin.html', users=users)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    # Handle password change
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Get the current admin password
        admin_password = Settings.get_value('admin_password', 'admin')
        
        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required', 'danger')
        elif current_password != admin_password:
            flash('Current password is incorrect', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'danger')
        elif len(new_password) < 4:
            flash('New password must be at least 4 characters long', 'danger')
        else:
            # Update the password
            Settings.set_value('admin_password', new_password)
            flash('Password updated successfully', 'success')
            
            # Redirect to avoid form resubmission
            return redirect(url_for('settings'))
    
    return render_template('settings.html')

@app.route('/api/task-status')
def get_task_status():
    """Get the status of the background task manager"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    status = task_manager.get_status()
    return jsonify({
        'success': True,
        'status': status
    })

@app.route('/restart-tasks')
def restart_tasks():
    """Restart the background task manager"""
    if not session.get('logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    task_manager.restart()
    flash('Background tasks restarted', 'success')
    
    # Redirect back to the referring page
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    else:
        return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/users/add', methods=['POST'])
def add_user():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    username = request.form.get('username')
    system_ip = request.form.get('system_ip')
    
    if not username or not system_ip:
        flash('Both username and system IP are required', 'danger')
        return redirect(url_for('admin'))
    
    # Check if user already exists
    existing_user = ManagedUser.query.filter_by(username=username, system_ip=system_ip).first()
    
    if existing_user:
        flash(f'User {username} on {system_ip} already exists', 'warning')
        return redirect(url_for('admin'))
    
    # Create new user
    new_user = ManagedUser(username=username, system_ip=system_ip)
    
    # Validate with timekpr
    ssh_client = SSHClient(hostname=system_ip)
    is_valid, message, config_dict = ssh_client.validate_user(username)
    
    new_user.is_valid = is_valid
    new_user.last_checked = datetime.utcnow()
    
    if is_valid and config_dict:
        new_user.last_config = json.dumps(config_dict)
        
        # Add the user to get an ID first
        db.session.add(new_user)
        db.session.commit()
        
        # Add today's usage data
        today = date.today()
        time_spent = config_dict.get('TIME_SPENT_DAY', 0)
        
        usage = UserTimeUsage(
            user_id=new_user.id,
            date=today,
            time_spent=time_spent
        )
        db.session.add(usage)
        db.session.commit()
        
        flash(f'User {username} added and validated successfully', 'success')
    else:
        db.session.add(new_user)
        db.session.commit()
        flash(f'User {username} added but validation failed: {message}', 'warning')
    
    return redirect(url_for('admin'))

@app.route('/users/validate/<int:user_id>')
def validate_user(user_id):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user = ManagedUser.query.get_or_404(user_id)
    
    # Validate with timekpr
    ssh_client = SSHClient(hostname=user.system_ip)
    is_valid, message, config_dict = ssh_client.validate_user(user.username)
    
    user.is_valid = is_valid
    user.last_checked = datetime.utcnow()
    
    if is_valid and config_dict:
        user.last_config = json.dumps(config_dict)
        
        # Update today's usage data
        today = date.today()
        time_spent = config_dict.get('TIME_SPENT_DAY', 0)
        
        # Look for an existing record for today
        usage = UserTimeUsage.query.filter_by(
            user_id=user.id,
            date=today
        ).first()
        
        if usage:
            usage.time_spent = time_spent
        else:
            # Create a new record
            usage = UserTimeUsage(
                user_id=user.id,
                date=today,
                time_spent=time_spent
            )
            db.session.add(usage)
        
        db.session.commit()
        flash(f'User {user.username} validated successfully', 'success')
    else:
        db.session.commit()
        flash(f'User validation failed: {message}', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user = ManagedUser.query.get_or_404(user_id)
    username = user.username
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} removed successfully', 'success')
    return redirect(url_for('admin'))

@app.route('/api/user/<int:user_id>/usage')
def get_user_usage(user_id):
    """API endpoint to get user usage data"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user = ManagedUser.query.get_or_404(user_id)
    days = request.args.get('days', 7, type=int)
    
    usage_data = user.get_recent_usage(days=days)
    
    # Format for chart.js
    labels = list(usage_data.keys())
    values = list(usage_data.values())
    
    # Convert seconds to hours for better readability
    values_hours = [round(v / 3600, 1) for v in values]
    
    return jsonify({
        'success': True,
        'labels': labels,
        'values': values_hours,
        'username': user.username
    })

@app.route('/api/modify-time', methods=['POST'])
def modify_time():
    """Modify time left for a user"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    # Get parameters from request
    user_id = request.form.get('user_id')
    operation = request.form.get('operation')
    seconds = request.form.get('seconds')
    
    if not user_id or not operation or not seconds:
        return jsonify({'success': False, 'message': 'Missing required parameters'}), 400
    
    try:
        user_id = int(user_id)
        seconds = int(seconds)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid parameter format'}), 400
    
    # Validate operation
    if operation not in ['+', '-']:
        return jsonify({'success': False, 'message': "Operation must be '+' or '-'"}), 400
    
    # Get user from database
    user = ManagedUser.query.get_or_404(user_id)
    
    # Create SSH client
    ssh_client = SSHClient(hostname=user.system_ip)
    
    # Execute the command
    success, message = ssh_client.modify_time_left(user.username, operation, seconds)
    
    if success:
        # Update user info to reflect changes
        is_valid, _, config_dict = ssh_client.validate_user(user.username)
        if is_valid and config_dict:
            user.last_checked = datetime.utcnow()
            user.last_config = json.dumps(config_dict)
            # Clear any pending adjustments since we succeeded
            user.pending_time_adjustment = None
            user.pending_time_operation = None
            db.session.commit()
            
        return jsonify({
            'success': True,
            'message': message,
            'username': user.username,
            'refresh': True
        })
    else:
        # Store as pending adjustment if it failed
        # First clear any existing pending adjustment
        user.pending_time_adjustment = seconds
        user.pending_time_operation = operation
        db.session.commit()
        
        return jsonify({
            'success': True,  # We report success since we stored it for later
            'message': f"Computer seems to be offline. Time adjustment of {operation}{seconds} seconds has been queued and will be applied when the computer comes online.",
            'username': user.username,
            'pending': True,
            'refresh': True
        })

# With app context
with app.app_context():
    db.create_all()
    print("Database tables verified")
    
    # Initialize admin password if it doesn't exist
    if not Settings.get_value('admin_password', None):
        Settings.set_value('admin_password', 'admin')
        print("Admin password initialized")
    
    # Start background tasks automatically
    task_manager.start()
    print("Background tasks started automatically")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)