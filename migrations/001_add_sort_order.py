MIGRATION_ID = 1
DESCRIPTION = "Add sort_order column to user_daily_time_interval"


def up(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(user_daily_time_interval)").fetchall()]
    if not cols or 'sort_order' in cols:
        return  # table absent (db.create_all will build it) or already migrated

    conn.executescript("""
        BEGIN;

        CREATE TABLE user_daily_time_interval_new (
            id           INTEGER PRIMARY KEY,
            user_id      INTEGER NOT NULL REFERENCES managed_user(id),
            day_of_week  INTEGER NOT NULL,
            start_hour   INTEGER NOT NULL,
            start_minute INTEGER DEFAULT 0,
            end_hour     INTEGER NOT NULL,
            end_minute   INTEGER DEFAULT 0,
            is_enabled   BOOLEAN DEFAULT 1,
            is_synced    BOOLEAN DEFAULT 0,
            last_synced  DATETIME,
            last_modified DATETIME,
            sort_order   INTEGER DEFAULT 0
        );

        INSERT INTO user_daily_time_interval_new
            SELECT id, user_id, day_of_week, start_hour, start_minute,
                   end_hour, end_minute, is_enabled, is_synced,
                   last_synced, last_modified, 0
            FROM user_daily_time_interval;

        DROP TABLE user_daily_time_interval;

        ALTER TABLE user_daily_time_interval_new
            RENAME TO user_daily_time_interval;

        COMMIT;
    """)
