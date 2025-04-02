import os
import sys
import shutil
import sqlite3

# List of potential cache files to remove
CACHE_FILES = [
    '__pycache__',
    '*.pyc',
    '.pytest_cache',
    '.cache',
    '.sqlalchemy_cache'
]

print("===== COMPLETE APPLICATION RESET =====")

# 1. Remove any __pycache__ directories
print("\nRemoving Python cache files...")
for root, dirs, files in os.walk('.'):
    for dir in dirs:
        if dir == '__pycache__':
            cache_path = os.path.join(root, dir)
            print(f"Removing: {cache_path}")
            shutil.rmtree(cache_path)
    for file in files:
        if file.endswith('.pyc'):
            pyc_path = os.path.join(root, file)
            print(f"Removing: {pyc_path}")
            os.remove(pyc_path)

# 2. Delete the existing database
DB_PATH = 'timekpr.db'
if os.path.exists(DB_PATH):
    print(f"\nRemoving existing database: {DB_PATH}")
    os.remove(DB_PATH)

# 3. Create a new database with proper schema
print("\nCreating new database with correct schema...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE managed_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL,
    system_ip VARCHAR(50) NOT NULL,
    is_valid BOOLEAN DEFAULT 0,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP,
    last_config TEXT,
    pending_time_adjustment INTEGER,
    pending_time_operation VARCHAR(1)
)
''')
print("Created managed_user table")

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

conn.commit()
conn.close()

# 4. Verify the schema
print("\nVerifying database schema...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(managed_user)")
columns = cursor.fetchall()
print("\nmanaged_user columns:")
for col in columns:
    print(f"- {col[1]} ({col[2]})")

cursor.execute("PRAGMA table_info(user_time_usage)")
columns = cursor.fetchall()
print("\nuser_time_usage columns:")
for col in columns:
    print(f"- {col[1]} ({col[2]})")

conn.close()

print("\n===== RESET COMPLETE =====")
print("Now restart your Python interpreter and run your application.")
print("IMPORTANT: Make sure to exit the Python interpreter completely and start a new one!")