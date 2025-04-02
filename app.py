from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
from datetime import datetime

from database import db, ManagedUser
from ssh_helper import SSHClient

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timekpr.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

# Hardcoded credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
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
    
    # Get all managed users
    users = ManagedUser.query.all()
    return render_template('dashboard.html', users=users)

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
        return redirect(url_for('dashboard'))
    
    # Check if user already exists
    existing_user = ManagedUser.query.filter_by(username=username, system_ip=system_ip).first()
    
    if existing_user:
        flash(f'User {username} on {system_ip} already exists', 'warning')
        return redirect(url_for('dashboard'))
    
    # Create new user
    new_user = ManagedUser(username=username, system_ip=system_ip)
    
    # Validate with timekpr
    ssh_client = SSHClient(hostname=system_ip)
    is_valid, message = ssh_client.validate_user(username)
    
    new_user.is_valid = is_valid
    new_user.last_checked = datetime.utcnow()
    
    # Save to database
    db.session.add(new_user)
    db.session.commit()
    
    if is_valid:
        flash(f'User {username} added and validated successfully', 'success')
    else:
        flash(f'User {username} added but validation failed: {message}', 'warning')
    
    return redirect(url_for('dashboard'))

@app.route('/users/validate/<int:user_id>')
def validate_user(user_id):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user = ManagedUser.query.get_or_404(user_id)
    
    # Validate with timekpr
    ssh_client = SSHClient(hostname=user.system_ip)
    is_valid, message = ssh_client.validate_user(user.username)
    
    user.is_valid = is_valid
    user.last_checked = datetime.utcnow()
    
    # Save to database
    db.session.commit()
    
    if is_valid:
        flash(f'User {user.username} validated successfully', 'success')
    else:
        flash(f'User validation failed: {message}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user = ManagedUser.query.get_or_404(user_id)
    username = user.username
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} removed successfully', 'success')
    return redirect(url_for('dashboard'))

# Create tables before first request (for Flask 2.0+)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)