"""
Glean Database Module

SQLite database schema and operations for the Glean pipeline.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


SCHEMA = """
-- Sources: where we discover tools (Reddit, Product Hunt, etc.)
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- e.g., "reddit", "producthunt", "web_search"
    url TEXT,                              -- specific URL if applicable
    reliability TEXT DEFAULT 'unrated',    -- authoritative, high, medium, low, unrated
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
    category TEXT,                         -- see glossary.md for taxonomy
    status TEXT DEFAULT 'inbox',           -- inbox, analyzing, review, approved, rejected
    relevance_score REAL,                  -- 0.0 to 1.0, set by curator
    rejection_reason TEXT,                 -- if rejected, why
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
    claim_type TEXT,                       -- feature, pricing, integration, limitation, comparison, use_case
    content TEXT NOT NULL,                 -- the claim text
    confidence REAL DEFAULT 0.5,           -- 0.0 to 1.0
    verified INTEGER DEFAULT 0,            -- 0 = unverified, 1 = verified
    conflicting INTEGER DEFAULT 0,         -- 0 = no conflict, 1 = conflicts with other claims
    raw_text TEXT,                         -- original source text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- Discoveries: raw scout findings before processing
CREATE TABLE IF NOT EXISTS discoveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    source_url TEXT NOT NULL,              -- specific URL where found
    raw_text TEXT NOT NULL,                -- original text content
    metadata TEXT,                         -- JSON: extra data (upvotes, author, etc.)
    processed INTEGER DEFAULT 0,           -- 0 = unprocessed, 1 = processed
    tool_id INTEGER,                       -- linked tool after processing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id),
    FOREIGN KEY (tool_id) REFERENCES tools(id)
);

-- Changelog: track changes to approved tools over time
CREATE TABLE IF NOT EXISTS changelog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id INTEGER NOT NULL,
    change_type TEXT NOT NULL,             -- new, pricing_change, feature_added, feature_removed, news
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
    content_hash TEXT,                     -- MD5 hash of page content
    pricing_text TEXT,                     -- extracted pricing info
    features_text TEXT,                    -- extracted features
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE
);

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

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status);
CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category);
CREATE INDEX IF NOT EXISTS idx_claims_tool ON claims(tool_id);
CREATE INDEX IF NOT EXISTS idx_claims_type ON claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_discoveries_processed ON discoveries(processed);
CREATE INDEX IF NOT EXISTS idx_changelog_tool ON changelog(tool_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_tool ON tool_snapshots(tool_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
"""


class Database:
    """SQLite database wrapper for Glean."""

    def __init__(self, db_path: str = "db/glean.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Connect to the database."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_schema(self):
        """Initialize the database schema."""
        conn = self.connect()
        conn.executescript(SCHEMA)
        conn.commit()
        self._seed_sources()

    def _seed_sources(self):
        """Seed default sources if they don't exist."""
        conn = self.connect()
        default_sources = [
            ("reddit", None, "medium"),
            ("producthunt", "https://www.producthunt.com", "high"),
            ("web_search", None, "medium"),
            ("twitter", "https://twitter.com", "medium"),
            ("hackernews", "https://news.ycombinator.com", "medium"),
        ]
        for name, url, reliability in default_sources:
            conn.execute(
                """INSERT OR IGNORE INTO sources (name, url, reliability)
                   VALUES (?, ?, ?)""",
                (name, url, reliability)
            )
        conn.commit()

    # --- Tool Operations ---

    def add_tool(self, name: str, url: str, description: str = None,
                 category: str = None, status: str = "inbox") -> int:
        """Add a new tool to the database."""
        conn = self.connect()
        cursor = conn.execute(
            """INSERT INTO tools (name, url, description, category, status)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(url) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
               RETURNING id""",
            (name, url, description, category, status)
        )
        tool_id = cursor.fetchone()[0]
        conn.commit()
        return tool_id

    def get_tool(self, tool_id: int) -> Optional[dict]:
        """Get a tool by ID."""
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM tools WHERE id = ?", (tool_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_tools_by_status(self, status: str) -> list[dict]:
        """Get all tools with a given status."""
        conn = self.connect()
        rows = conn.execute(
            "SELECT * FROM tools WHERE status = ? ORDER BY relevance_score DESC, created_at DESC",
            (status,)
        ).fetchall()
        return [dict(row) for row in rows]

    def update_tool_status(self, tool_id: int, status: str,
                           rejection_reason: str = None):
        """Update a tool's pipeline status."""
        conn = self.connect()
        if status == "rejected" and rejection_reason:
            conn.execute(
                """UPDATE tools SET status = ?, rejection_reason = ?,
                   reviewed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (status, rejection_reason, tool_id)
            )
        elif status in ("approved", "rejected"):
            conn.execute(
                """UPDATE tools SET status = ?, reviewed_at = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (status, tool_id)
            )
        else:
            conn.execute(
                "UPDATE tools SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, tool_id)
            )
        conn.commit()

    def set_relevance_score(self, tool_id: int, score: float):
        """Set a tool's relevance score."""
        conn = self.connect()
        conn.execute(
            "UPDATE tools SET relevance_score = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (score, tool_id)
        )
        conn.commit()

    # --- Claim Operations ---

    def add_claim(self, tool_id: int, source_id: int, content: str,
                  claim_type: str = None, confidence: float = 0.5,
                  raw_text: str = None) -> int:
        """Add a claim about a tool."""
        conn = self.connect()
        cursor = conn.execute(
            """INSERT INTO claims (tool_id, source_id, claim_type, content, confidence, raw_text)
               VALUES (?, ?, ?, ?, ?, ?)
               RETURNING id""",
            (tool_id, source_id, claim_type, content, confidence, raw_text)
        )
        claim_id = cursor.fetchone()[0]
        conn.commit()
        return claim_id

    def get_claims_for_tool(self, tool_id: int) -> list[dict]:
        """Get all claims for a tool."""
        conn = self.connect()
        rows = conn.execute(
            """SELECT c.*, s.name as source_name, s.reliability as source_reliability
               FROM claims c
               JOIN sources s ON c.source_id = s.id
               WHERE c.tool_id = ?
               ORDER BY c.confidence DESC""",
            (tool_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    # --- Discovery Operations ---

    def add_discovery(self, source_id: int, source_url: str, raw_text: str,
                      metadata: dict = None) -> int:
        """Add a raw discovery from a scout."""
        conn = self.connect()
        cursor = conn.execute(
            """INSERT INTO discoveries (source_id, source_url, raw_text, metadata)
               VALUES (?, ?, ?, ?)
               RETURNING id""",
            (source_id, source_url, raw_text, json.dumps(metadata) if metadata else None)
        )
        discovery_id = cursor.fetchone()[0]
        conn.commit()
        return discovery_id

    def get_unprocessed_discoveries(self, limit: int = 100) -> list[dict]:
        """Get unprocessed discoveries for analysis."""
        conn = self.connect()
        rows = conn.execute(
            """SELECT d.*, s.name as source_name, s.reliability as source_reliability
               FROM discoveries d
               JOIN sources s ON d.source_id = s.id
               WHERE d.processed = 0
               ORDER BY d.created_at ASC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_discovery_processed(self, discovery_id: int, tool_id: int = None):
        """Mark a discovery as processed, optionally linking to a tool."""
        conn = self.connect()
        conn.execute(
            "UPDATE discoveries SET processed = 1, tool_id = ? WHERE id = ?",
            (tool_id, discovery_id)
        )
        conn.commit()

    # --- Source Operations ---

    def get_source_by_name(self, name: str) -> Optional[dict]:
        """Get a source by name."""
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM sources WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None

    def update_source_stats(self, source_id: int, useful: bool):
        """Update source reliability statistics."""
        conn = self.connect()
        if useful:
            conn.execute(
                """UPDATE sources SET
                   total_discoveries = total_discoveries + 1,
                   useful_discoveries = useful_discoveries + 1,
                   updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (source_id,)
            )
        else:
            conn.execute(
                """UPDATE sources SET
                   total_discoveries = total_discoveries + 1,
                   updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (source_id,)
            )
        conn.commit()

    # --- Changelog Operations ---

    def add_changelog_entry(self, tool_id: int, change_type: str,
                            description: str, source_url: str = None) -> int:
        """Add a changelog entry for a tool."""
        conn = self.connect()
        cursor = conn.execute(
            """INSERT INTO changelog (tool_id, change_type, description, source_url)
               VALUES (?, ?, ?, ?)
               RETURNING id""",
            (tool_id, change_type, description, source_url)
        )
        entry_id = cursor.fetchone()[0]
        conn.commit()
        return entry_id

    def get_recent_changes(self, days: int = 7, limit: int = 100) -> list[dict]:
        """Get recent changelog entries."""
        conn = self.connect()
        rows = conn.execute(
            """SELECT c.*, t.name as tool_name, t.url as tool_url
               FROM changelog c
               JOIN tools t ON c.tool_id = t.id
               WHERE c.detected_at >= datetime('now', ?)
               ORDER BY c.detected_at DESC
               LIMIT ?""",
            (f'-{days} days', limit)
        ).fetchall()
        return [dict(row) for row in rows]

    # --- User Operations ---

    def create_user(self, username: str, email: str, password_hash: str,
                    is_admin: bool = False) -> int:
        """Create a new user."""
        conn = self.connect()
        cursor = conn.execute(
            """INSERT INTO users (username, email, password_hash, is_admin)
               VALUES (?, ?, ?, ?)
               RETURNING id""",
            (username, email, password_hash, 1 if is_admin else 0)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
        return user_id

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Get a user by username."""
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get a user by email."""
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Get a user by ID."""
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_last_login(self, user_id: int):
        """Update user's last login timestamp."""
        conn = self.connect()
        conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        conn.commit()

    def get_user_count(self) -> int:
        """Get total number of users."""
        conn = self.connect()
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    # --- Statistics ---

    def get_pipeline_stats(self) -> dict:
        """Get pipeline statistics."""
        conn = self.connect()

        # Count tools by status
        status_counts = {}
        for status in ['inbox', 'analyzing', 'review', 'approved', 'rejected']:
            count = conn.execute(
                "SELECT COUNT(*) FROM tools WHERE status = ?", (status,)
            ).fetchone()[0]
            status_counts[status] = count

        # Count unprocessed discoveries
        unprocessed = conn.execute(
            "SELECT COUNT(*) FROM discoveries WHERE processed = 0"
        ).fetchone()[0]

        # Count total claims
        total_claims = conn.execute(
            "SELECT COUNT(*) FROM claims"
        ).fetchone()[0]

        # Count sources
        sources = conn.execute(
            "SELECT COUNT(*) FROM sources"
        ).fetchone()[0]

        return {
            "tools_by_status": status_counts,
            "total_tools": sum(status_counts.values()),
            "unprocessed_discoveries": unprocessed,
            "total_claims": total_claims,
            "total_sources": sources,
        }


def init_database(db_path: str = "db/glean.db"):
    """Initialize the database with schema."""
    db = Database(db_path)
    db.init_schema()
    print(f"Database initialized at {db_path}")
    return db


if __name__ == "__main__":
    # Initialize database when run directly
    init_database()
