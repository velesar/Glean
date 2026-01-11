"""
API Dependencies

Shared dependencies for API routers.
"""

from src.database import Database

# Global database instance
_db: Database = None


def get_db() -> Database:
    """Get database instance."""
    global _db
    if _db is None:
        _db = Database()
        _db.init_schema()
    return _db


def init_db():
    """Initialize database on startup."""
    global _db
    _db = Database()
    _db.init_schema()


def close_db():
    """Close database on shutdown."""
    global _db
    if _db:
        _db.close()
        _db = None
