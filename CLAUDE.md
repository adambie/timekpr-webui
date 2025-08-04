# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a Flask-based web application that provides remote management for Timekpr-nExT (Linux parental control software). The app manages multiple computers via SSH connections to control time limits for users across the network.

## Development Commands

### Running the Application
```bash
# Using Python directly
python app.py  # Starts Flask dev server on 0.0.0.0:5000

# Using Docker (recommended for production)
docker-compose up -d  # Builds and starts container with port mapping

# Manual setup (alternative)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Database Management
```bash
# Reset database (removes all data)
python reset_db.py

# Database is created automatically on first run via app.py
```

## Architecture

### Core Components
- **app.py**: Main Flask application with all routes and web interface logic
- **src/database.py**: SQLAlchemy models for Settings, ManagedUser, and UserTimeUsage
- **src/ssh_helper.py**: SSH client wrapper for executing timekpra commands on remote systems
- **src/task_manager.py**: Background thread manager that periodically updates user data and applies pending time adjustments

### Key Features
- **Background Task System**: Continuously monitors managed PCs and applies time changes to offline systems when they come online
- **SSH-based Remote Control**: Uses paramiko to execute timekpra commands on remote Linux systems
- **Time Usage Tracking**: Stores daily usage data and displays weekly charts
- **Pending Adjustments**: Queues time modifications for offline systems

### Database Schema
- **Settings**: Key-value store for app configuration (admin password)  
- **ManagedUser**: Tracks username, system IP, validation status, and pending time adjustments
- **UserTimeUsage**: Daily time usage records linked to managed users

### Authentication
- Single admin user with configurable password (stored in Settings table)
- Password is shared between web login and SSH connections to managed systems
- Default credentials: admin/admin (should be changed in Settings page)

### Remote System Requirements
Each managed PC needs:
- Timekpr-nExT installed
- User 'timekpr-remote' created and added to 'timekpr' group
- SSH access configured
- Same password for 'timekpr-remote' user as web admin password

## Development Notes

### Flask Configuration
- SQLite database: `timekpr.db` (created automatically)
- Templates in `templates/` directory
- Static files in `static/` directory
- Session-based authentication

### Background Processing
- Background task manager runs in daemon thread
- 10-second polling interval for user data updates
- Thread-safe with locks to prevent concurrent execution
- Automatic restart capability via web interface

### SSH Operations
- Validates users with `timekpra --userinfo [username]`
- Modifies time with `timekpra --settimeleft [username] [+/-] [seconds]`
- Parses timekpr output into structured configuration data
- Handles connection failures gracefully