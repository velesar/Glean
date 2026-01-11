"""
Tests for the Glean Database module.
"""

import os

import pytest

from src.database import Database


class TestDatabaseInitialization:
    """Tests for database initialization."""

    def test_create_database(self, temp_db_path):
        """Test database creation."""
        db = Database(temp_db_path)
        db.init_schema()

        assert os.path.exists(temp_db_path)
        db.close()

    def test_init_schema_creates_tables(self, temp_db):
        """Test that init_schema creates all required tables."""
        db = temp_db

        # Check tables exist by querying sqlite_master
        conn = db.connect()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row['name'] for row in cursor.fetchall()}

        expected_tables = {'sources', 'tools', 'claims', 'discoveries', 'changelog'}
        assert expected_tables.issubset(tables)

    def test_init_schema_idempotent(self, temp_db):
        """Test that init_schema can be called multiple times safely."""
        db = temp_db

        # Call init_schema again - should not raise
        db.init_schema()
        db.init_schema()

        # Should still work
        stats = db.get_pipeline_stats()
        assert isinstance(stats, dict)


class TestToolOperations:
    """Tests for tool CRUD operations."""

    def test_add_tool(self, temp_db):
        """Test adding a tool."""
        db = temp_db

        tool_id = db.add_tool(
            name="Test Tool",
            url="https://test.com",
            description="A test tool",
            category="Testing",
            status="inbox"
        )

        assert tool_id is not None
        assert isinstance(tool_id, int)

    def test_get_tool(self, temp_db):
        """Test retrieving a tool by ID."""
        db = temp_db

        tool_id = db.add_tool(
            name="Test Tool",
            url="https://test.com",
            description="A test tool",
            category="Testing",
            status="inbox"
        )

        tool = db.get_tool(tool_id)

        assert tool is not None
        assert tool['name'] == "Test Tool"
        assert tool['url'] == "https://test.com"
        assert tool['description'] == "A test tool"
        assert tool['category'] == "Testing"
        assert tool['status'] == "inbox"

    def test_get_nonexistent_tool(self, temp_db):
        """Test retrieving a nonexistent tool."""
        db = temp_db
        tool = db.get_tool(9999)
        assert tool is None

    def test_get_tools_by_status(self, temp_db):
        """Test retrieving tools by status."""
        db = temp_db

        # Add tools with different statuses
        db.add_tool(name="Tool 1", url="https://tool1.com", status="inbox")
        db.add_tool(name="Tool 2", url="https://tool2.com", status="inbox")
        db.add_tool(name="Tool 3", url="https://tool3.com", status="review")
        db.add_tool(name="Tool 4", url="https://tool4.com", status="approved")

        inbox_tools = db.get_tools_by_status("inbox")
        review_tools = db.get_tools_by_status("review")
        approved_tools = db.get_tools_by_status("approved")

        assert len(inbox_tools) == 2
        assert len(review_tools) == 1
        assert len(approved_tools) == 1

    def test_update_tool_status(self, temp_db):
        """Test updating tool status."""
        db = temp_db

        tool_id = db.add_tool(name="Test Tool", url="https://test.com", status="inbox")

        # Update to review
        db.update_tool_status(tool_id, "review")
        tool = db.get_tool(tool_id)
        assert tool['status'] == "review"

        # Update to approved
        db.update_tool_status(tool_id, "approved")
        tool = db.get_tool(tool_id)
        assert tool['status'] == "approved"

    def test_update_tool_status_with_rejection_reason(self, temp_db):
        """Test updating tool status with rejection reason."""
        db = temp_db

        tool_id = db.add_tool(name="Test Tool", url="https://test.com", status="review")

        db.update_tool_status(tool_id, "rejected", rejection_reason="Not relevant")
        tool = db.get_tool(tool_id)

        assert tool['status'] == "rejected"
        assert tool['rejection_reason'] == "Not relevant"

class TestDiscoveryOperations:
    """Tests for discovery operations."""

    def test_add_discovery(self, temp_db):
        """Test adding a discovery."""
        db = temp_db

        # Get a source ID first
        source = db.get_source_by_name("reddit")
        source_id = source['id'] if source else 1

        discovery_id = db.add_discovery(
            source_id=source_id,
            source_url="https://reddit.com/r/test/1",
            raw_text="This is a test discovery",
            metadata={"subreddit": "test"}
        )

        assert discovery_id is not None
        assert isinstance(discovery_id, int)

    def test_get_unprocessed_discoveries(self, temp_db):
        """Test getting unprocessed discoveries."""
        db = temp_db

        source = db.get_source_by_name("reddit")
        source_id = source['id'] if source else 1

        # Add some discoveries
        db.add_discovery(
            source_id=source_id,
            source_url="https://reddit.com/1",
            raw_text="Discovery 1"
        )
        db.add_discovery(
            source_id=source_id,
            source_url="https://reddit.com/2",
            raw_text="Discovery 2"
        )

        discoveries = db.get_unprocessed_discoveries()

        assert len(discoveries) == 2

    def test_get_unprocessed_discoveries_with_limit(self, temp_db):
        """Test getting unprocessed discoveries with limit."""
        db = temp_db

        source = db.get_source_by_name("reddit")
        source_id = source['id'] if source else 1

        # Add 5 discoveries
        for i in range(5):
            db.add_discovery(
                source_id=source_id,
                source_url=f"https://reddit.com/{i}",
                raw_text=f"Discovery {i}"
            )

        discoveries = db.get_unprocessed_discoveries(limit=3)

        assert len(discoveries) == 3

    def test_mark_discovery_processed(self, temp_db):
        """Test marking discovery as processed."""
        db = temp_db

        source = db.get_source_by_name("reddit")
        source_id = source['id'] if source else 1

        discovery_id = db.add_discovery(
            source_id=source_id,
            source_url="https://reddit.com/1",
            raw_text="Test discovery"
        )

        # Initially unprocessed
        unprocessed = db.get_unprocessed_discoveries()
        assert len(unprocessed) == 1

        # Mark as processed
        db.mark_discovery_processed(discovery_id)

        # Should be empty now
        unprocessed = db.get_unprocessed_discoveries()
        assert len(unprocessed) == 0


class TestClaimOperations:
    """Tests for claim operations."""

    def test_add_claim(self, temp_db):
        """Test adding a claim."""
        db = temp_db

        tool_id = db.add_tool(name="Test Tool", url="https://test.com", status="inbox")
        source = db.get_source_by_name("reddit")
        source_id = source['id'] if source else 1

        claim_id = db.add_claim(
            tool_id=tool_id,
            source_id=source_id,
            content="This tool has AI features",
            claim_type="feature",
            confidence=0.9
        )

        assert claim_id is not None
        assert isinstance(claim_id, int)

    def test_get_claims_for_tool(self, temp_db):
        """Test getting claims for a tool."""
        db = temp_db

        tool_id = db.add_tool(name="Test Tool", url="https://test.com", status="inbox")
        source = db.get_source_by_name("reddit")
        source_id = source['id'] if source else 1

        # Add multiple claims
        db.add_claim(
            tool_id=tool_id,
            source_id=source_id,
            content="Claim 1",
            claim_type="feature",
            confidence=0.8
        )
        db.add_claim(
            tool_id=tool_id,
            source_id=source_id,
            content="Claim 2",
            claim_type="pricing",
            confidence=0.7
        )

        claims = db.get_claims_for_tool(tool_id)

        assert len(claims) == 2
        assert claims[0]['content'] in ["Claim 1", "Claim 2"]


class TestChangelogOperations:
    """Tests for changelog operations."""

    def test_add_changelog_entry(self, temp_db):
        """Test adding a changelog entry."""
        db = temp_db

        tool_id = db.add_tool(name="Test Tool", url="https://test.com", status="approved")

        db.add_changelog_entry(
            tool_id=tool_id,
            change_type="new",
            description="Tool approved"
        )

        # Verify by checking recent changes
        changes = db.get_recent_changes(days=1)
        assert len(changes) >= 1


class TestPipelineStats:
    """Tests for pipeline statistics."""

    def test_get_pipeline_stats_empty(self, temp_db):
        """Test getting stats from empty database."""
        db = temp_db

        stats = db.get_pipeline_stats()

        assert 'total_tools' in stats
        assert 'tools_by_status' in stats
        assert 'unprocessed_discoveries' in stats
        assert 'total_claims' in stats
        assert 'total_sources' in stats

    def test_get_pipeline_stats_with_data(self, temp_db):
        """Test getting stats with data."""
        db = temp_db

        # Add some tools
        db.add_tool(name="Tool 1", url="https://tool1.com", status="inbox")
        db.add_tool(name="Tool 2", url="https://tool2.com", status="review")
        db.add_tool(name="Tool 3", url="https://tool3.com", status="approved")

        stats = db.get_pipeline_stats()

        assert stats['total_tools'] >= 3
        assert stats['tools_by_status']['inbox'] >= 1
        assert stats['tools_by_status']['review'] >= 1
        assert stats['tools_by_status']['approved'] >= 1


class TestSourceOperations:
    """Tests for source operations."""

    def test_default_sources_seeded(self, temp_db):
        """Test that default sources are seeded."""
        db = temp_db

        conn = db.connect()
        cursor = conn.execute("SELECT COUNT(*) as count FROM sources")
        count = cursor.fetchone()['count']

        # Should have default sources
        assert count >= 1

    def test_get_source_by_name(self, temp_db):
        """Test getting source by name."""
        db = temp_db

        source = db.get_source_by_name("reddit")
        assert source is not None
        assert source['name'] == "reddit"


class TestDatabaseConnection:
    """Tests for database connection handling."""

    def test_close_and_reopen(self, temp_db_path):
        """Test closing and reopening database."""
        db = Database(temp_db_path)
        db.init_schema()

        # Add some data
        tool_id = db.add_tool(name="Test", url="https://test.com", status="inbox")

        # Close
        db.close()

        # Reopen
        db2 = Database(temp_db_path)
        tool = db2.get_tool(tool_id)

        assert tool is not None
        assert tool['name'] == "Test"

        db2.close()

    def test_row_factory(self, temp_db):
        """Test that row factory returns dict-like objects."""
        db = temp_db

        tool_id = db.add_tool(name="Test", url="https://test.com", status="inbox")
        tool = db.get_tool(tool_id)

        # Should be accessible by key
        assert tool['name'] == "Test"
        assert tool['status'] == "inbox"
