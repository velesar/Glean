"""
Migration: Add Users Table
Created: 2026-01-11

Adds authentication support with users table for the web UI.
"""


def up(conn):
    """Apply the migration."""
    conn.executescript("""
        -- Users: authentication and authorization
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );

        -- Indexes for user lookups
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """)


def down(conn):
    """Rollback the migration."""
    conn.executescript("""
        DROP INDEX IF EXISTS idx_users_email;
        DROP INDEX IF EXISTS idx_users_username;
        DROP TABLE IF EXISTS users;
    """)
