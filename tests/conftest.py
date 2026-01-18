"""
Test fixtures for Glean CLI tests.
"""

import os
import tempfile

import pytest
from click.testing import CliRunner

from src.database import Database


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_db():
    """Create a temporary database for testing.

    Uses check_same_thread=False to allow use with FastAPI TestClient
    which runs in a different thread.
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = Database(db_path, check_same_thread=False)
    db.init_schema()

    yield db

    # Cleanup
    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def temp_db_path():
    """Return a path to a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def isolated_filesystem(tmp_path):
    """Run test in an isolated filesystem."""
    original_dir = os.getcwd()
    os.chdir(tmp_path)

    yield tmp_path

    os.chdir(original_dir)


@pytest.fixture
def mock_config(monkeypatch, temp_db_path):
    """Mock the config loading to use temp database."""
    def mock_load_config():
        return {
            "database": {"path": temp_db_path},
            "api_keys": {}
        }

    monkeypatch.setattr("src.cli.load_config", mock_load_config)
    monkeypatch.setattr("src.config.load_config", mock_load_config)

    return temp_db_path
