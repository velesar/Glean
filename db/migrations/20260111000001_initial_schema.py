"""
Migration: Initial Schema
Created: 2026-01-11

Creates the core Glean database schema:
- sources: Where we discover tools
- tools: AI tools discovered by scouts
- claims: Discrete statements about tools
- discoveries: Raw scout findings
- changelog: Track changes to approved tools
- tool_snapshots: Periodic snapshots for change detection
"""


def up(conn):
    """Apply the migration."""
    conn.executescript("""
        -- Sources: where we discover tools (Reddit, Product Hunt, etc.)
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT,
            reliability TEXT DEFAULT 'unrated',
            total_discoveries INTEGER DEFAULT 0,
            useful_discoveries INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Tools: AI tools discovered by scouts
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT,
            description TEXT,
            category TEXT,
            status TEXT DEFAULT 'inbox',
            relevance_score REAL,
            rejection_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            UNIQUE(url)
        );

        -- Claims: discrete statements about tools, extracted from sources
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            claim_type TEXT,
            content TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            verified INTEGER DEFAULT 0,
            conflicting INTEGER DEFAULT 0,
            raw_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        );

        -- Discoveries: raw scout findings before processing
        CREATE TABLE IF NOT EXISTS discoveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            source_url TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            metadata TEXT,
            processed INTEGER DEFAULT 0,
            tool_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources(id),
            FOREIGN KEY (tool_id) REFERENCES tools(id)
        );

        -- Changelog: track changes to approved tools over time
        CREATE TABLE IF NOT EXISTS changelog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            description TEXT NOT NULL,
            source_url TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE
        );

        -- Tool Snapshots: periodic snapshots of tool webpages for change detection
        CREATE TABLE IF NOT EXISTS tool_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            title TEXT,
            content_hash TEXT,
            pricing_text TEXT,
            features_text TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE
        );

        -- Indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status);
        CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category);
        CREATE INDEX IF NOT EXISTS idx_claims_tool ON claims(tool_id);
        CREATE INDEX IF NOT EXISTS idx_claims_type ON claims(claim_type);
        CREATE INDEX IF NOT EXISTS idx_discoveries_processed ON discoveries(processed);
        CREATE INDEX IF NOT EXISTS idx_changelog_tool ON changelog(tool_id);
        CREATE INDEX IF NOT EXISTS idx_snapshots_tool ON tool_snapshots(tool_id);

        -- Seed default sources
        INSERT OR IGNORE INTO sources (name, url, reliability) VALUES
            ('reddit', NULL, 'medium'),
            ('producthunt', 'https://www.producthunt.com', 'high'),
            ('web_search', NULL, 'medium'),
            ('twitter', 'https://twitter.com', 'medium'),
            ('hackernews', 'https://news.ycombinator.com', 'medium');
    """)


def down(conn):
    """Rollback the migration."""
    conn.executescript("""
        DROP INDEX IF EXISTS idx_snapshots_tool;
        DROP INDEX IF EXISTS idx_changelog_tool;
        DROP INDEX IF EXISTS idx_discoveries_processed;
        DROP INDEX IF EXISTS idx_claims_type;
        DROP INDEX IF EXISTS idx_claims_tool;
        DROP INDEX IF EXISTS idx_tools_category;
        DROP INDEX IF EXISTS idx_tools_status;

        DROP TABLE IF EXISTS tool_snapshots;
        DROP TABLE IF EXISTS changelog;
        DROP TABLE IF EXISTS discoveries;
        DROP TABLE IF EXISTS claims;
        DROP TABLE IF EXISTS tools;
        DROP TABLE IF EXISTS sources;
    """)
