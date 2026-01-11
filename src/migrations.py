"""
Database Migration System

A lightweight migration system for SQLite databases.
Tracks applied migrations and supports up/down migrations.
"""

import importlib.util
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "migrations"
MIGRATIONS_TABLE = "_migrations"


class MigrationError(Exception):
    """Migration-related error."""
    pass


class Migrator:
    """Database migration manager."""

    def __init__(self, db_path: str = "db/glean.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Get database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        conn = self.connect()
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    def get_applied_migrations(self) -> list[str]:
        """Get list of applied migration names."""
        self.init_migrations_table()
        conn = self.connect()
        rows = conn.execute(
            f"SELECT name FROM {MIGRATIONS_TABLE} ORDER BY id"
        ).fetchall()
        return [row["name"] for row in rows]

    def get_pending_migrations(self) -> list[str]:
        """Get list of pending migration names."""
        applied = set(self.get_applied_migrations())
        available = self.get_available_migrations()
        return [m for m in available if m not in applied]

    def get_available_migrations(self) -> list[str]:
        """Get list of all available migration files, sorted by timestamp."""
        if not MIGRATIONS_DIR.exists():
            return []

        migrations = []
        pattern = re.compile(r"^\d{14}_\w+\.py$")

        for f in MIGRATIONS_DIR.iterdir():
            if f.is_file() and pattern.match(f.name):
                migrations.append(f.stem)

        return sorted(migrations)

    def load_migration(self, name: str):
        """Load a migration module."""
        migration_path = MIGRATIONS_DIR / f"{name}.py"
        if not migration_path.exists():
            raise MigrationError(f"Migration file not found: {migration_path}")

        spec = importlib.util.spec_from_file_location(name, migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "up"):
            raise MigrationError(f"Migration {name} missing 'up' function")

        return module

    def run_migration(self, name: str, direction: str = "up"):
        """Run a single migration up or down."""
        module = self.load_migration(name)
        conn = self.connect()

        func = getattr(module, direction, None)
        if func is None:
            if direction == "down":
                raise MigrationError(f"Migration {name} does not support rollback")
            raise MigrationError(f"Migration {name} missing '{direction}' function")

        try:
            func(conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise MigrationError(f"Migration {name} failed: {e}")

    def migrate(self, steps: Optional[int] = None) -> list[str]:
        """
        Apply pending migrations.

        Args:
            steps: Number of migrations to apply (None = all)

        Returns:
            List of applied migration names
        """
        self.init_migrations_table()
        pending = self.get_pending_migrations()

        if steps is not None:
            pending = pending[:steps]

        applied = []
        conn = self.connect()

        for name in pending:
            self.run_migration(name, "up")
            conn.execute(
                f"INSERT INTO {MIGRATIONS_TABLE} (name) VALUES (?)",
                (name,)
            )
            conn.commit()
            applied.append(name)

        return applied

    def rollback(self, steps: int = 1) -> list[str]:
        """
        Rollback applied migrations.

        Args:
            steps: Number of migrations to rollback

        Returns:
            List of rolled back migration names
        """
        self.init_migrations_table()
        applied = self.get_applied_migrations()

        to_rollback = list(reversed(applied[-steps:]))
        rolled_back = []
        conn = self.connect()

        for name in to_rollback:
            self.run_migration(name, "down")
            conn.execute(
                f"DELETE FROM {MIGRATIONS_TABLE} WHERE name = ?",
                (name,)
            )
            conn.commit()
            rolled_back.append(name)

        return rolled_back

    def reset(self) -> list[str]:
        """Rollback all migrations."""
        applied = self.get_applied_migrations()
        return self.rollback(len(applied))

    def refresh(self) -> tuple[list[str], list[str]]:
        """Reset and re-run all migrations."""
        rolled_back = self.reset()
        applied = self.migrate()
        return rolled_back, applied

    def status(self) -> dict:
        """Get migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        return {
            "applied": applied,
            "pending": pending,
            "total_applied": len(applied),
            "total_pending": len(pending),
        }


def create_migration(name: str, template: str = "default") -> Path:
    """
    Create a new migration file.

    Args:
        name: Migration name (will be snake_cased)
        template: Template to use ('default' or 'table')

    Returns:
        Path to created migration file
    """
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate timestamp prefix
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Clean up name
    clean_name = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

    filename = f"{timestamp}_{clean_name}.py"
    filepath = MIGRATIONS_DIR / filename

    if template == "table":
        content = f'''"""
Migration: {name}
Created: {datetime.now().isoformat()}
"""


def up(conn):
    """Apply the migration."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS table_name (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def down(conn):
    """Rollback the migration."""
    conn.execute("DROP TABLE IF EXISTS table_name")
'''
    else:
        content = f'''"""
Migration: {name}
Created: {datetime.now().isoformat()}
"""


def up(conn):
    """Apply the migration."""
    pass


def down(conn):
    """Rollback the migration."""
    pass
'''

    filepath.write_text(content)
    return filepath
