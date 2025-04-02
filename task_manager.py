import threading
import time
import sqlite3
from datetime import datetime, date
import logging
import json

from database import db, ManagedUser, UserTimeUsage
from ssh_helper import SSHClient

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    def __init__(self, app=None):
        self.app = app
        self.running = False
        self.thread = None
    
    def init_app(self, app):
        self.app = app
    
    def start(self):
        """Start the background task manager"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_tasks, daemon=True)
        self.thread.start()
        logger.info("Background task manager started")
    
    def restart(self):
        """Restart the background task manager"""
        self.stop()
        time.sleep(1)  # Give it a moment to fully stop
        self.start()
        logger.info("Background task manager restarted")
        
    def get_status(self):
        """Get the status of the background task manager"""
        return {
            'running': self.running,
            'thread_alive': self.thread.is_alive() if self.thread else False,
            'last_error': getattr(self, 'last_error', None)
        }
    
    def _run_tasks(self):
        """Main task loop"""
        while self.running:
            try:
                with self.app.app_context():
                    self._update_user_data()
                self.last_error = None  # Clear error on successful run
            except Exception as e:
                error_msg = f"Error in background task: {str(e)}"
                logger.error(error_msg)
                self.last_error = {
                    'message': error_msg,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Sleep for 5 minutes before next run
            for _ in range(300):  # 5 minutes * 60 seconds
                if not self.running:
                    break
                time.sleep(1)
    
    def _update_user_data(self):
        """Update data for all valid users"""
        try:
            # First verify that the database schema is correct
            with sqlite3.connect('timekpr.db') as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(managed_user)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'last_config' not in columns:
                    logger.error("Database schema is incorrect: 'last_config' column is missing")
                    return
            
            valid_users = ManagedUser.query.filter_by(is_valid=True).all()
            
            for user in valid_users:
                try:
                    # Connect to the system and get user info
                    ssh_client = SSHClient(hostname=user.system_ip)
                    is_valid, _, config_dict = ssh_client.validate_user(user.username)
                    
                    if is_valid and config_dict:
                        # Update the last checked time
                        user.last_checked = datetime.utcnow()
                        user.last_config = json.dumps(config_dict)
                        
                        # Update or create today's usage data
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
                        logger.info(f"Updated usage data for {user.username}")
                    else:
                        logger.warning(f"Failed to get data for {user.username}")
                
                except Exception as e:
                    logger.error(f"Error updating user {user.username}: {str(e)}")
                    # Continue with the next user
        
        except Exception as e:
            logger.error(f"Error in user data update: {str(e)}")