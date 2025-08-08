from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    
    @classmethod
    def get_value(cls, key, default=None):
        """Get a setting value by key"""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set_value(cls, key, value):
        """Set a setting value by key"""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting

class ManagedUser(db.Model):
    __tablename__ = 'managed_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    system_ip = db.Column(db.String(50), nullable=False)
    is_valid = db.Column(db.Boolean, default=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked = db.Column(db.DateTime, nullable=True)
    last_config = db.Column(db.Text, nullable=True) # Store the full config JSON
    pending_time_adjustment = db.Column(db.Integer, nullable=True) # Pending time adjustment in seconds
    pending_time_operation = db.Column(db.String(1), nullable=True) # + or -
    
    # Relationship with usage data and weekly schedules
    usage_data = db.relationship('UserTimeUsage', backref='user', lazy=True, cascade="all, delete-orphan")
    weekly_schedule = db.relationship('UserWeeklySchedule', backref='user', uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<ManagedUser {self.username}@{self.system_ip}>'
    
    def get_recent_usage(self, days=7):
        """Get usage data for the last n days"""
        today = datetime.utcnow().date()
        start_date = today - timedelta(days=days-1)
        
        # Get the usage records for the specified period
        records = UserTimeUsage.query.filter_by(user_id=self.id).filter(
            UserTimeUsage.date >= start_date,
            UserTimeUsage.date <= today
        ).order_by(UserTimeUsage.date).all()
        
        # Create a dict with all days in the period
        usage_dict = {}
        for i in range(days):
            date = start_date + timedelta(days=i)
            usage_dict[date.strftime('%Y-%m-%d')] = 0
        
        # Fill in the actual data
        for record in records:
            date_str = record.date.strftime('%Y-%m-%d')
            usage_dict[date_str] = record.time_spent
        
        return usage_dict
    
    def get_config_value(self, key):
        """Extract a specific value from the stored config"""
        if not self.last_config:
            return None
        try:
            config = json.loads(self.last_config)
            return config.get(key)
        except:
            return None

class UserTimeUsage(db.Model):
    __tablename__ = 'user_time_usage'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('managed_user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_spent = db.Column(db.Integer, default=0) # Time spent in seconds
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='user_date_uc'),
    )
    
    def __repr__(self):
        return f'<UserTimeUsage {self.user.username} {self.date}: {self.time_spent}>'

class UserWeeklySchedule(db.Model):
    __tablename__ = 'user_weekly_schedule'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('managed_user.id'), nullable=False)
    
    # Time limits per day in hours (0 = no limit/disabled)
    monday_hours = db.Column(db.Float, default=0)
    tuesday_hours = db.Column(db.Float, default=0)
    wednesday_hours = db.Column(db.Float, default=0)
    thursday_hours = db.Column(db.Float, default=0)
    friday_hours = db.Column(db.Float, default=0)
    saturday_hours = db.Column(db.Float, default=0)
    sunday_hours = db.Column(db.Float, default=0)
    
    # Sync status and timestamps
    is_synced = db.Column(db.Boolean, default=False)
    last_synced = db.Column(db.DateTime, nullable=True)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserWeeklySchedule {self.user.username}>'
    
    def get_schedule_dict(self):
        """Get schedule as a dictionary for easy template rendering"""
        return {
            'monday': self.monday_hours,
            'tuesday': self.tuesday_hours,
            'wednesday': self.wednesday_hours,
            'thursday': self.thursday_hours,
            'friday': self.friday_hours,
            'saturday': self.saturday_hours,
            'sunday': self.sunday_hours
        }
    
    def set_schedule_from_dict(self, schedule_dict):
        """Set schedule from a dictionary"""
        self.monday_hours = schedule_dict.get('monday', 0)
        self.tuesday_hours = schedule_dict.get('tuesday', 0)
        self.wednesday_hours = schedule_dict.get('wednesday', 0)
        self.thursday_hours = schedule_dict.get('thursday', 0)
        self.friday_hours = schedule_dict.get('friday', 0)
        self.saturday_hours = schedule_dict.get('saturday', 0)
        self.sunday_hours = schedule_dict.get('sunday', 0)
        self.last_modified = datetime.utcnow()
        self.is_synced = False
    
    def set_weekdays_hours(self, hours):
        """Set the same hours for all weekdays (Monday to Friday)"""
        self.monday_hours = hours
        self.tuesday_hours = hours
        self.wednesday_hours = hours
        self.thursday_hours = hours
        self.friday_hours = hours
        self.last_modified = datetime.utcnow()
        self.is_synced = False
    
    def has_pending_changes(self):
        """Check if there are unsynced changes"""
        return not self.is_synced
    
    def mark_synced(self):
        """Mark the schedule as synced with the remote system"""
        self.is_synced = True
        self.last_synced = datetime.utcnow()

class UserDailyTimeInterval(db.Model):
    __tablename__ = 'user_daily_time_interval'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('managed_user.id'), nullable=False)
    
    # Day of week (1=Monday, 7=Sunday, matching ISO 8601)
    day_of_week = db.Column(db.Integer, nullable=False)  # 1-7
    
    # Time interval (24-hour format)
    start_hour = db.Column(db.Integer, nullable=False)   # 0-23
    start_minute = db.Column(db.Integer, default=0)      # 0-59
    end_hour = db.Column(db.Integer, nullable=False)     # 0-23
    end_minute = db.Column(db.Integer, default=0)        # 0-59
    
    # Whether this interval is enabled
    is_enabled = db.Column(db.Boolean, default=True)
    
    # Sync status and timestamps
    is_synced = db.Column(db.Boolean, default=False)
    last_synced = db.Column(db.DateTime, nullable=True)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship back to user
    user = db.relationship('ManagedUser', backref='time_intervals')
    
    # Constraint to ensure only one interval per user per day
    __table_args__ = (
        db.UniqueConstraint('user_id', 'day_of_week', name='user_day_interval_uc'),
    )
    
    def __repr__(self):
        return f'<UserDailyTimeInterval {self.user.username} Day{self.day_of_week} {self.start_hour:02d}:{self.start_minute:02d}-{self.end_hour:02d}:{self.end_minute:02d}>'
    
    def get_time_range_string(self):
        """Get formatted time range string (e.g., '09:00-17:30')"""
        return f"{self.start_hour:02d}:{self.start_minute:02d}-{self.end_hour:02d}:{self.end_minute:02d}"
    
    def get_day_name(self):
        """Get day name from day_of_week number"""
        days = ['', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[self.day_of_week] if 1 <= self.day_of_week <= 7 else 'Unknown'
    
    def is_valid_interval(self):
        """Check if the time interval is valid (start < end, within 24h)"""
        start_minutes = self.start_hour * 60 + self.start_minute
        end_minutes = self.end_hour * 60 + self.end_minute
        return start_minutes < end_minutes and 0 <= start_minutes < 1440 and 0 <= end_minutes < 1440
    
    def mark_synced(self):
        """Mark the interval as synced with the remote system"""
        self.is_synced = True
        self.last_synced = datetime.utcnow()
    
    def mark_modified(self):
        """Mark the interval as modified (needs sync)"""
        self.is_synced = False
        self.last_modified = datetime.utcnow()
    
    def to_timekpr_format(self):
        """Convert interval to timekpr hour specification format"""
        if not self.is_enabled:
            return None
        
        # If full hour intervals, just return the hour numbers
        if self.start_minute == 0 and self.end_minute == 0:
            hours = list(range(self.start_hour, self.end_hour))
            return [str(h) for h in hours]
        
        # If partial hours, include minute specifications
        result = []
        current_hour = self.start_hour
        
        # First hour (potentially partial)
        if current_hour == self.end_hour:
            # Same hour, use minute range
            result.append(f"{current_hour}[{self.start_minute}-{self.end_minute}]")
        else:
            # Multiple hours
            if self.start_minute == 0:
                result.append(str(current_hour))
            else:
                result.append(f"{current_hour}[{self.start_minute}-59]")
            
            current_hour += 1
            
            # Full hours in between
            while current_hour < self.end_hour:
                result.append(str(current_hour))
                current_hour += 1
            
            # Last hour (potentially partial)
            if self.end_minute > 0:
                result.append(f"{self.end_hour}[0-{self.end_minute}]")
        
        return result