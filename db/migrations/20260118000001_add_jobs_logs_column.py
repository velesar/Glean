"""
Migration: Add logs column to jobs table for storing job execution logs.

Up: Adds logs column to jobs table
Down: Drops logs column from jobs table
"""


def up(conn):
    """Apply migration."""
    conn.executescript("""
        -- Add logs column to jobs table (JSON array of log entries)
        ALTER TABLE jobs ADD COLUMN logs TEXT DEFAULT '[]';
    """)


def down(conn):
    """Rollback migration."""
    # SQLite doesn't support DROP COLUMN directly in older versions
    # We'll create a new table without the column and copy data
    conn.executescript("""
        CREATE TABLE jobs_backup AS SELECT
            id, type, status, progress, message, result, error,
            scout_type, config, user_id, started_at, completed_at
        FROM jobs;

        DROP TABLE jobs;

        CREATE TABLE jobs (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            message TEXT DEFAULT '',
            result TEXT,
            error TEXT,
            scout_type TEXT,
            config TEXT,
            user_id INTEGER,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        INSERT INTO jobs SELECT * FROM jobs_backup;
        DROP TABLE jobs_backup;

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type);
        CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_started_at ON jobs(started_at);
    """)
