"""
Lightweight schema migration runner.

Migrations live in the top-level migrations/ directory. Each file must define:
  MIGRATION_ID   int   — unique, determines run order
  DESCRIPTION    str   — shown in logs and stored in schema_migrations
  up(conn)             — applies the migration; must be idempotent

Applied migrations are tracked in the schema_migrations table so every
migration runs exactly once, regardless of how many times the app starts.
"""
import importlib.util
import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')


def _db_path(app):
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if uri.startswith('sqlite:////'):
        return uri[len('sqlite:////'):]
    if uri.startswith('sqlite:///'):
        return os.path.join(app.instance_path, uri[len('sqlite:///'):])
    raise ValueError(f"Unsupported DB URI for migration runner: {uri}")


def _ensure_migrations_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id          INTEGER PRIMARY KEY,
            description TEXT    NOT NULL,
            applied_at  DATETIME DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def _load_migrations():
    if not os.path.isdir(MIGRATIONS_DIR):
        return []
    migrations = []
    for fname in sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.py') and not f.startswith('_')):
        path = os.path.join(MIGRATIONS_DIR, fname)
        spec = importlib.util.spec_from_file_location(fname[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        migrations.append(mod)
    migrations.sort(key=lambda m: m.MIGRATION_ID)
    return migrations


def run_migrations(app):
    path = _db_path(app)
    conn = sqlite3.connect(path)
    try:
        _ensure_migrations_table(conn)
        applied = {row[0] for row in conn.execute("SELECT id FROM schema_migrations").fetchall()}
        for m in _load_migrations():
            if m.MIGRATION_ID in applied:
                continue
            logger.info("Applying migration %d: %s", m.MIGRATION_ID, m.DESCRIPTION)
            m.up(conn)
            conn.execute(
                "INSERT INTO schema_migrations (id, description) VALUES (?, ?)",
                (m.MIGRATION_ID, m.DESCRIPTION),
            )
            conn.commit()
            logger.info("Migration %d applied", m.MIGRATION_ID)
    finally:
        conn.close()
