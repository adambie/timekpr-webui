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
    
    # Relationship with usage data
    usage_data = db.relationship('UserTimeUsage', backref='user', lazy=True, cascade="all, delete-orphan")
    
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