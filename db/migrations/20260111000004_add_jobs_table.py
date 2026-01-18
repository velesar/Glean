"""
Migration: Add jobs table for persisting background job state.

Up: Creates jobs table
Down: Drops jobs table
"""


def up(conn):
    """Apply migration."""
    conn.executescript("""
        -- Jobs: track background job execution
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,                 -- scout, analyze, curate, update
            status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
            progress INTEGER DEFAULT 0,
            message TEXT DEFAULT '',
            result TEXT,                        -- JSON: job-specific results
            error TEXT,
            scout_type TEXT,                    -- for scout jobs only
            config TEXT,                        -- JSON: job configuration
            user_id INTEGER,                    -- user who started the job
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Indexes for job queries
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type);
        CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_started_at ON jobs(started_at);
    """)


def down(conn):
    """Rollback migration."""
    conn.executescript("""
        DROP INDEX IF EXISTS idx_jobs_started_at;
        DROP INDEX IF EXISTS idx_jobs_user;
        DROP INDEX IF EXISTS idx_jobs_type;
        DROP INDEX IF EXISTS idx_jobs_status;
        DROP TABLE IF EXISTS jobs;
    """)
