import threading
import time
import sqlite3
from datetime import datetime, date
import logging
import json
import traceback

from database import db, ManagedUser, UserTimeUsage
from ssh_helper import SSHClient

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    def __init__(self, app=None):
        self.app = app
        self.running = False
        self.thread = None
        self.last_error = None
        self._task_lock = threading.Lock()  # Add a lock to prevent concurrent executions
    
    def init_app(self, app):
        self.app = app
    
    def start(self):
        """Start the background task manager"""
        if self.running:
            logger.info("Task manager already running, not starting again")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_tasks, daemon=True)
        self.thread.start()
        logger.info("Background task manager started with thread ID: %s", self.thread.ident)
    
    def stop(self):
        """Stop the background task manager"""
        logger.info("Stopping background task manager...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            logger.info("Thread joined: %s", not self.thread.is_alive())
        logger.info("Background task manager stopped")
    
    def restart(self):
        """Restart the background task manager"""
        logger.info("Restarting background task manager...")
        self.stop()
        time.sleep(1)  # Give it a moment to fully stop
        self.start()
        logger.info("Background task manager restarted")
        
    def get_status(self):
        """Get the status of the background task manager"""
        status = {
            'running': self.running,
            'thread_alive': self.thread.is_alive() if self.thread else False,
            'last_error': self.last_error,
            'thread_id': self.thread.ident if self.thread else None
        }
        logger.info("Task manager status: %s", status)
        return status
    
    def _run_tasks(self):
        """Main task loop"""
        logger.info("Task loop started in thread ID: %s", threading.current_thread().ident)
        while self.running:
            try:
                # Only process tasks if we can acquire the lock
                if self._task_lock.acquire(blocking=False):
                    try:
                        logger.info("Starting task execution cycle")
                        # Use a fresh app context
                        if self.app:
                            with self.app.app_context():
                                logger.info("Updating user data")
                                self._update_user_data()
                                logger.info("User data update cycle complete")
                        else:
                            logger.error("App is not initialized in task manager")
                        
                        self.last_error = None  # Clear error on successful run
                    finally:
                        self._task_lock.release()
                else:
                    logger.info("Task already running, skipping this cycle")
            except Exception as e:
                if self._task_lock.locked():
                    self._task_lock.release()
                error_msg = f"Error in background task: {str(e)}"
                trace = traceback.format_exc()
                logger.error("%s\n%s", error_msg, trace)
                self.last_error = {
                    'message': error_msg,
                    'trace': trace,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Sleep for 10 seconds before next run
            logger.info("Task cycle finished, sleeping for 10 seconds")
            for i in range(10):
                if not self.running:
                    logger.info("Task loop stopping during sleep")
                    break
                time.sleep(1)
    
    def _update_user_data(self):
        """Update data for all valid users"""
        try:
            # Get all users with SQLAlchemy in a single query
            users = ManagedUser.query.all()
            logger.info("Found %d users in database", len(users))

            for user in users:
                try:
                    logger.info("Processing user: %s @ %s", user.username, user.system_ip)
                    
                    # Connect to the system and get user info
                    ssh_client = SSHClient(hostname=user.system_ip)
                    
                    # Check if there's a pending time adjustment
                    if user.pending_time_adjustment is not None and user.pending_time_operation is not None:
                        logger.info(f"Attempting to apply pending time adjustment for {user.username}: {user.pending_time_operation}{user.pending_time_adjustment} seconds")
                        
                        success, message = ssh_client.modify_time_left(
                            user.username, 
                            user.pending_time_operation, 
                            user.pending_time_adjustment
                        )
                        
                        if success:
                            logger.info(f"Successfully applied pending time adjustment for {user.username}")
                            # Clear the pending adjustment immediately
                            user.pending_time_adjustment = None
                            user.pending_time_operation = None
                            db.session.commit()
                            logger.info("Cleared pending adjustment in database")
                        else:
                            logger.warning(f"Failed to apply pending time adjustment for {user.username}: {message}")
                    else:
                        logger.info(f"No pending time adjustment for {user.username}")
                    
# Then update user info
                    logger.info("Validating user %s", user.username)
                    try:
                        is_valid, result_message, config_dict = ssh_client.validate_user(user.username)
                        logger.info("Validation result for %s: %s", user.username, is_valid)
                        
                        if is_valid and config_dict:
                            # Update the last checked time
                            user.last_checked = datetime.utcnow()
                            user.last_config = json.dumps(config_dict)
                            user.is_valid = True  # Ensure is_valid is set to True
                            
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
                                logger.info(f"Updated existing usage record for {user.username}, time_spent={time_spent}")
                            else:
                                # Create a new record
                                usage = UserTimeUsage(
                                    user_id=user.id,
                                    date=today,
                                    time_spent=time_spent
                                )
                                db.session.add(usage)
                                logger.info(f"Created new usage record for {user.username}, time_spent={time_spent}")
                            
                            # Make sure to commit after each user update
                            db.session.commit()
                            logger.info(f"Database committed for {user.username}")
                        else:
                            # Just update the last checked time
                            user.last_checked = datetime.utcnow()
                            
                            # Don't change is_valid status for temporary failures
                            # This allows the user to stay visible on the dashboard
                            # Only set is_valid to False during the initial validation
                            if not user.is_valid and is_valid:
                                # If the user was previously invalid but is now valid, update status
                                user.is_valid = True
                            
                            db.session.commit()
                            logger.warning(f"Failed to get data for {user.username}, keeping previous valid status")
                    except Exception as e:
                        # Connection error (e.g., PC is offline)
                        logger.error(f"Connection error for user {user.username}: {str(e)}")
                        
                        # Update the last checked time but don't change validation status
                        user.last_checked = datetime.utcnow()
                        db.session.commit()
                        logger.info(f"Updated last_checked time for {user.username} but kept validation status")
                
                except Exception as e:
                    logger.error(f"Error updating user {user.username}: {str(e)}\n{traceback.format_exc()}")
                    # Continue with the next user, but make sure we commit any pending changes
                    db.session.rollback()
                    
        except Exception as e:
            logger.error(f"Error in user data update: {str(e)}\n{traceback.format_exc()}")
            db.session.rollback()