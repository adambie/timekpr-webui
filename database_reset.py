import os
import sys
import sqlite3

# Make sure we're in the right directory
print("Current directory:", os.getcwd())

# Delete the existing database file if it exists
if os.path.exists('timekpr.db'):
    os.remove('timekpr.db')
    print("Removed existing database")

# Import our Flask application to use its context
try:
    from app import app, db
    print("Successfully imported app")
except ImportError as e:
    print(f"Error importing app: {e}")
    sys.exit(1)

# Create all tables using our app context
try:
    with app.app_context():
        db.drop_all()  # Ensure all tables are dropped first
        print("Dropped all tables")
        
        db.create_all()
        print("Database tables created successfully")
        
        # Verify tables were created correctly
        tables = []
        with sqlite3.connect('timekpr.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [table[0] for table in cursor.fetchall()]
            
            # Check columns in managed_user table
            cursor.execute(f"PRAGMA table_info(managed_user)")
            columns = cursor.fetchall()
            print("\nmanaged_user table columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        
        print(f"\nCreated tables: {', '.join(tables)}")
except Exception as e:
    print(f"Error creating database: {e}")
    sys.exit(1)

print("\nDatabase reset completed successfully.")