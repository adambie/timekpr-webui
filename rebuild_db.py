import os
import sys
import sqlite3

# Make sure all imports are available from root directory
sys.path.insert(0, os.getcwd())

# Delete the existing database file if it exists
DB_PATH = 'timekpr.db'
if os.path.exists(DB_PATH):
    print(f"Removing existing database file: {DB_PATH}")
    os.remove(DB_PATH)

# Create the database manually with explicit schema
print("Creating new database...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create managed_user table with the last_config column
cursor.execute('''
CREATE TABLE managed_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL,
    system_ip VARCHAR(50) NOT NULL,
    is_valid BOOLEAN DEFAULT 0,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP,
    last_config TEXT
)
''')
print("Created managed_user table")

# Create user_time_usage table
cursor.execute('''
CREATE TABLE user_time_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    time_spent INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES managed_user (id) ON DELETE CASCADE,
    UNIQUE (user_id, date)
)
''')
print("Created user_time_usage table")

# Commit changes and close connection
conn.commit()
conn.close()

# Verify tables and columns
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("\nCreated tables:")
for table in tables:
    print(f"- {table[0]}")

# Check managed_user columns
cursor.execute("PRAGMA table_info(managed_user)")
columns = cursor.fetchall()
print("\nmanaged_user columns:")
for col in columns:
    print(f"- {col[1]} ({col[2]})")

# Check user_time_usage columns
cursor.execute("PRAGMA table_info(user_time_usage)")
columns = cursor.fetchall()
print("\nuser_time_usage columns:")
for col in columns:
    print(f"- {col[1]} ({col[2]})")

conn.close()

print("\nDatabase rebuilt successfully!")
print("Now you can run your Flask application.")