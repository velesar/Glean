"""
Migration: Add Settings Table
Created: 2026-01-11

Adds a settings table for storing user configuration and API credentials.
Settings are stored as key-value pairs with optional encryption for secrets.
"""


def up(conn):
    """Apply the migration."""
    conn.executescript("""
        -- Settings: user configuration and API credentials
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,           -- 'api_keys', 'preferences', 'scouts', etc.
            key TEXT NOT NULL,                -- setting key within category
            value TEXT,                       -- setting value (may be encrypted)
            is_secret INTEGER DEFAULT 0,      -- 1 if value is encrypted/sensitive
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, category, key)
        );

        -- Index for fast lookups
        CREATE INDEX IF NOT EXISTS idx_settings_user ON settings(user_id);
        CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(user_id, category);
    """)


def down(conn):
    """Rollback the migration."""
    conn.executescript("""
        DROP INDEX IF EXISTS idx_settings_category;
        DROP INDEX IF EXISTS idx_settings_user;
        DROP TABLE IF EXISTS settings;
    """)
