"""
DEPRECATED: this one-shot script is superseded by the migration runner.
The equivalent logic lives in migrations/001_add_sort_order.py and runs
automatically on app startup via src/migrator.py.

Kept here only for reference.
"""
import sqlite3
import os
import sys

DB_PATHS = [
    '/app/instance/timekpr.db',
    os.path.join(os.path.dirname(__file__), 'instance', 'timekpr.db'),
    'instance/timekpr.db',
]

def find_db():
    for p in DB_PATHS:
        if os.path.exists(p):
            return p
    return None

def migrate(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_daily_time_interval'")
    if not cur.fetchone():
        print("Table user_daily_time_interval does not exist — nothing to migrate.")
        conn.close()
        return

    # Check if sort_order already exists (migration already ran)
    cur.execute("PRAGMA table_info(user_daily_time_interval)")
    cols = [row[1] for row in cur.fetchall()]
    if 'sort_order' in cols:
        print("sort_order column already exists — migration already applied.")
        conn.close()
        return

    print(f"Migrating {db_path} ...")

    cur.executescript("""
        BEGIN;

        CREATE TABLE user_daily_time_interval_new (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES managed_user(id),
            day_of_week INTEGER NOT NULL,
            start_hour INTEGER NOT NULL,
            start_minute INTEGER DEFAULT 0,
            end_hour INTEGER NOT NULL,
            end_minute INTEGER DEFAULT 0,
            is_enabled BOOLEAN DEFAULT 1,
            is_synced BOOLEAN DEFAULT 0,
            last_synced DATETIME,
            last_modified DATETIME,
            sort_order INTEGER DEFAULT 0
        );

        INSERT INTO user_daily_time_interval_new
            (id, user_id, day_of_week, start_hour, start_minute,
             end_hour, end_minute, is_enabled, is_synced,
             last_synced, last_modified, sort_order)
        SELECT id, user_id, day_of_week, start_hour, start_minute,
               end_hour, end_minute, is_enabled, is_synced,
               last_synced, last_modified, 0
        FROM user_daily_time_interval;

        DROP TABLE user_daily_time_interval;

        ALTER TABLE user_daily_time_interval_new
            RENAME TO user_daily_time_interval;

        COMMIT;
    """)

    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else find_db()
    if not path:
        print("Database not found. Pass the path as argument or run from project root.")
        sys.exit(1)
    migrate(path)
