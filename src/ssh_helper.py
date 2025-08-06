import paramiko
import time
from datetime import datetime
import re
import json
from src.database import Settings

class SSHClient:
    def __init__(self, hostname, username='timekpr-remote', password=None, port=22):
        self.hostname = hostname
        self.username = username
        self.password = password if password else Settings.get_value('admin_password', 'admin')
        self.port = port
        
    def validate_user(self, username):
        """
        Check if a user exists by running the timekpra --userinfo command
        Returns: (is_valid, message, config_dict)
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                port=self.port,
                timeout=10
            )
            
            command = f'timekpra --userinfo {username}'
            stdin, stdout, stderr = client.exec_command(command)
            
            # Wait for command to complete
            exit_status = stdout.channel.recv_exit_status()
            
            # Read output
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            # Check for the error message indicating user not found
            if f'User "{username}" configuration is not found' in output or f'User "{username}" configuration is not found' in error:
                return False, f"User '{username}' not found on system", None
            
            # Parse the configuration
            config_dict = self._parse_timekpr_output(output)
            
            # If we get here, the user likely exists
            return True, output, config_dict
            
        except Exception as e:
            return False, f"Connection error: {str(e)}", None
        finally:
            try:
                client.close()
            except:
                pass
    
    def _parse_timekpr_output(self, output):
        """Parse the output of timekpra --userinfo command into a dictionary"""
        config_dict = {}
        
        # Regular expression to match key-value pairs
        pattern = r'([A-Z_]+):\s*(.*)'
        
        for line in output.split('\n'):
            match = re.search(pattern, line)
            if match:
                key = match.group(1)
                value = match.group(2).strip()
                
                # Convert numeric values
                if value.isdigit():
                    value = int(value)
                elif ';' in value:
                    # Handle semicolon-separated lists
                    value = value.split(';')
                    # Convert to integers if possible
                    if all(item.isdigit() for item in value):
                        value = [int(item) for item in value]
                elif value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                
                config_dict[key] = value
                
        return config_dict
        
    def modify_time_left(self, username, operation, seconds):
        """
        Modify time left for a user using timekpra --settimeleft command
        operation should be '+' or '-'
        seconds is the amount of time to add or remove
        
        Returns: (success, message)
        """
        if operation not in ['+', '-']:
            return False, "Invalid operation. Must be '+' or '-'"
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                port=self.port,
                timeout=10
            )
            
            command = f'timekpra --settimeleft {username} {operation} {seconds}'
            stdin, stdout, stderr = client.exec_command(command)
            
            # Wait for command to complete
            exit_status = stdout.channel.recv_exit_status()
            
            # Read output
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            if exit_status == 0:
                return True, f"Successfully modified time for {username}: {operation}{seconds} seconds"
            else:
                return False, f"Error modifying time: {error}"
            
        except Exception as e:
            return False, f"Connection error: {str(e)}"
        finally:
            try:
                client.close()
            except:
                pass
    
    def set_weekly_time_limits(self, username, schedule_dict):
        """
        Set daily time limits for a user using timekpra commands
        schedule_dict should contain day names (monday, tuesday, etc.) with hour values
        
        Returns: (success, message)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                port=self.port,
                timeout=10
            )
            
            # First, let's check what the current user configuration looks like
            check_command = f'timekpra --userinfo {username}'
            logger.info(f"Checking current user config: {check_command}")
            stdin, stdout, stderr = client.exec_command(check_command)
            exit_status = stdout.channel.recv_exit_status()
            user_info = stdout.read().decode('utf-8')
            logger.info(f"Current user info: {user_info}")
            
            # Step 1: Set allowed days (1=Monday, 7=Sunday)
            # Find days that have time limits > 0
            allowed_days = []
            day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            for i, day in enumerate(day_order):
                hours = schedule_dict.get(day, 0)
                if hours > 0:
                    allowed_days.append(str(i + 1))  # 1=Monday, 7=Sunday
            
            if not allowed_days:
                logger.warning("No days with time limits > 0 found")
                return False, "No days with time limits configured"
            
            # Set allowed days
            allowed_days_string = ';'.join(allowed_days)
            # Try without sudo first, then with sudo if needed
            days_command = f'timekpra --setalloweddays {username} \'{allowed_days_string}\''
            logger.info(f"Setting allowed days: {days_command}")
            
            stdin, stdout, stderr = client.exec_command(days_command)
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            logger.info(f"Set allowed days - exit status: {exit_status}, output: {output}, error: {error}")
            
            if exit_status != 0:
                logger.info("Trying with sudo...")
                days_command = f'sudo timekpra --setalloweddays {username} \'{allowed_days_string}\''
                logger.info(f"Setting allowed days with sudo: {days_command}")
                
                stdin, stdout, stderr = client.exec_command(days_command)
                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode('utf-8')
                error = stderr.read().decode('utf-8')
                
                logger.info(f"Set allowed days with sudo - exit status: {exit_status}, output: {output}, error: {error}")
                
                if exit_status != 0:
                    return False, f"Failed to set allowed days (tried with and without sudo): {error if error else output}"
            
            # Step 2: Set time limits for the allowed days only
            time_limits = []
            for i, day in enumerate(day_order):
                hours = schedule_dict.get(day, 0)
                if hours > 0:  # Only include days with limits
                    seconds = int(hours * 3600)  # Convert to integer seconds
                    time_limits.append(str(seconds))
            
            if time_limits:
                time_limit_string = ';'.join(time_limits)
                # Try without sudo first, then with sudo if needed  
                limits_command = f'timekpra --settimelimits {username} \'{time_limit_string}\''
                logger.info(f"Setting time limits: {limits_command}")
                
                stdin, stdout, stderr = client.exec_command(limits_command)
                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode('utf-8')
                error = stderr.read().decode('utf-8')
                
                logger.info(f"Set time limits - exit status: {exit_status}, output: {output}, error: {error}")
                logger.info(f"DEBUG - schedule_dict received: {schedule_dict}")
                logger.info(f"DEBUG - time_limits calculated: {time_limits}")
                logger.info(f"DEBUG - allowed_days: {allowed_days}")
                
                if exit_status != 0:
                    logger.info("Trying time limits with sudo...")
                    limits_command = f'sudo timekpra --settimelimits {username} \'{time_limit_string}\''
                    logger.info(f"Setting time limits with sudo: {limits_command}")
                    
                    stdin, stdout, stderr = client.exec_command(limits_command)
                    exit_status = stdout.channel.recv_exit_status()
                    output = stdout.read().decode('utf-8')
                    error = stderr.read().decode('utf-8')
                    
                    logger.info(f"Set time limits with sudo - exit status: {exit_status}, output: {output}, error: {error}")
                    
                    if exit_status != 0:
                        return False, f"Failed to set time limits (tried with and without sudo): {error if error else output}"
            
            return True, f"Successfully configured daily time limits for {username}. Days: {allowed_days_string}, Limits: {time_limits}"
            
        except Exception as e:
            logger.error(f"Exception in set_weekly_time_limits: {str(e)}")
            return False, f"Connection error: {str(e)}"
        finally:
            try:
                client.close()
            except:
                pass