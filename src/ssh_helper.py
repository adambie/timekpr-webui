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
            
            if exit_status == 127:
                return False, f"timekpra not found on {self.hostname}", None
                
            # A german error message - but exit code is zero
            if f'Zugriff verweigert' in output or f'Zugriff verweigert' in error:
                return False, f"Insufficient privileges", None
            
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