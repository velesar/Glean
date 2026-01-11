"""
Tests for the Glean CLI.
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from src.cli import main, init, status, scout, analyze, curate, migrate
from src.database import Database


class TestCLIMain:
    """Tests for main CLI group."""

    def test_main_help(self, runner):
        """Test that main help command works."""
        result = runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'Glean' in result.output
        assert 'AI Sales Tool Intelligence' in result.output

    def test_main_version(self, runner):
        """Test that version flag works."""
        result = runner.invoke(main, ['--version'])
        assert result.exit_code == 0
        assert '0.1.0' in result.output


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_database(self, runner, mock_config):
        """Test that init command initializes the database."""
        result = runner.invoke(main, ['init'])
        assert result.exit_code == 0
        assert 'Database initialized' in result.output

    def test_init_without_config_file(self, runner, mock_config, tmp_path):
        """Test init shows warning when config.yaml is missing."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ['init'])
            assert result.exit_code == 0
            assert 'No config.yaml found' in result.output

    def test_init_with_config_file(self, runner, mock_config, tmp_path):
        """Test init shows success when config.yaml exists."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config.yaml in current directory (which is tmp_path)
            from pathlib import Path
            Path("config.yaml").write_text("database:\n  path: db/glean.db\n")

            result = runner.invoke(main, ['init'])
            assert result.exit_code == 0
            assert 'Configuration loaded' in result.output


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_with_empty_db(self, runner, mock_config):
        """Test status command with empty database."""
        # First init the database
        runner.invoke(main, ['init'])

        result = runner.invoke(main, ['status'])
        assert result.exit_code == 0
        assert 'Pipeline Status' in result.output

    def test_status_without_init(self, runner, temp_db_path, monkeypatch):
        """Test status command when database doesn't exist."""
        # Use non-existent db path
        def mock_load_config():
            return {"database": {"path": "/nonexistent/path/db.db"}}

        monkeypatch.setattr("src.cli.load_config", mock_load_config)

        result = runner.invoke(main, ['status'])
        # Should show error about database not initialized
        assert 'Database not initialized' in result.output or result.exit_code != 0

    def test_status_shows_all_stages(self, runner, mock_config):
        """Test that status shows all pipeline stages."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['status'])

        assert result.exit_code == 0
        assert 'Inbox' in result.output
        assert 'Analyzing' in result.output
        assert 'Review' in result.output
        assert 'Approved' in result.output
        assert 'Rejected' in result.output


class TestScoutCommands:
    """Tests for scout commands."""

    def test_scout_help(self, runner):
        """Test scout help command."""
        result = runner.invoke(main, ['scout', '--help'])
        assert result.exit_code == 0
        assert 'reddit' in result.output
        assert 'twitter' in result.output
        assert 'producthunt' in result.output
        assert 'web' in result.output
        assert 'rss' in result.output
        assert 'all' in result.output

    def test_scout_reddit_demo(self, runner, mock_config):
        """Test Reddit scout in demo mode."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['scout', 'reddit', '--demo'])

        assert result.exit_code == 0
        assert 'Reddit scout' in result.output
        assert 'Demo' in result.output
        assert 'Scout complete' in result.output

    def test_scout_reddit_with_options(self, runner, mock_config):
        """Test Reddit scout with options."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['scout', 'reddit', '--demo', '--limit', '10'])

        assert result.exit_code == 0
        assert 'Scout complete' in result.output

    def test_scout_twitter_demo(self, runner, mock_config):
        """Test Twitter scout in demo mode."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['scout', 'twitter', '--demo'])

        assert result.exit_code == 0
        assert 'Twitter scout' in result.output
        assert 'Demo' in result.output

    def test_scout_producthunt_demo(self, runner, mock_config):
        """Test Product Hunt scout in demo mode."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['scout', 'producthunt', '--demo'])

        assert result.exit_code == 0
        assert 'Product Hunt scout' in result.output
        assert 'Demo' in result.output

    def test_scout_web_demo(self, runner, mock_config):
        """Test Web Search scout in demo mode."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['scout', 'web', '--demo'])

        assert result.exit_code == 0
        assert 'Web Search scout' in result.output
        assert 'Demo' in result.output

    def test_scout_rss_demo(self, runner, mock_config):
        """Test RSS scout in demo mode."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['scout', 'rss', '--demo'])

        assert result.exit_code == 0
        assert 'RSS scout' in result.output
        assert 'Demo' in result.output

    def test_scout_all_demo(self, runner, mock_config):
        """Test running all scouts in demo mode."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['scout', 'all', '--demo'])

        assert result.exit_code == 0
        assert 'Running all scouts' in result.output


class TestAnalyzeCommand:
    """Tests for the analyze command."""

    def test_analyze_no_discoveries(self, runner, mock_config):
        """Test analyze with no unprocessed discoveries."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['analyze'])

        assert result.exit_code == 0
        assert 'No unprocessed discoveries' in result.output

    def test_analyze_mock_mode(self, runner, mock_config):
        """Test analyze in mock mode with discoveries."""
        runner.invoke(main, ['init'])
        # Add some discoveries first
        runner.invoke(main, ['scout', 'reddit', '--demo'])

        result = runner.invoke(main, ['analyze', '--mock'])

        assert result.exit_code == 0
        # Should either process or say no discoveries
        assert 'Analysis complete' in result.output or 'No unprocessed discoveries' in result.output

    def test_analyze_with_limit(self, runner, mock_config):
        """Test analyze with limit option."""
        runner.invoke(main, ['init'])
        runner.invoke(main, ['scout', 'reddit', '--demo'])

        result = runner.invoke(main, ['analyze', '--mock', '--limit', '5'])

        assert result.exit_code == 0


class TestCurateCommand:
    """Tests for the curate command."""

    def test_curate_no_tools(self, runner, mock_config):
        """Test curate with no tools to curate."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['curate'])

        assert result.exit_code == 0
        assert 'No tools to curate' in result.output

    def test_curate_with_options(self, runner, mock_config):
        """Test curate with custom options."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['curate', '--min-score', '0.5', '--no-merge'])

        assert result.exit_code == 0


class TestMigrateCommands:
    """Tests for migration commands."""

    def test_migrate_help(self, runner):
        """Test migrate help command."""
        result = runner.invoke(main, ['migrate', '--help'])
        assert result.exit_code == 0
        assert 'status' in result.output
        assert 'run' in result.output
        assert 'rollback' in result.output
        assert 'create' in result.output

    def test_migrate_status(self, runner, mock_config):
        """Test migrate status command."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['migrate', 'status'])

        assert result.exit_code == 0
        assert 'Migration Status' in result.output

    def test_migrate_run_no_pending(self, runner, mock_config):
        """Test migrate run with no pending migrations."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['migrate', 'run'])

        assert result.exit_code == 0
        assert 'No pending migrations' in result.output or 'migration' in result.output.lower()


class TestReportCommands:
    """Tests for report commands."""

    def test_report_help(self, runner):
        """Test report help command."""
        result = runner.invoke(main, ['report', '--help'])
        assert result.exit_code == 0
        assert 'weekly' in result.output
        assert 'changelog' in result.output
        assert 'index' in result.output

    def test_report_weekly(self, runner, mock_config):
        """Test weekly report generation."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['report', 'weekly'])

        assert result.exit_code == 0
        assert 'Generating weekly digest' in result.output

    def test_report_changelog(self, runner, mock_config):
        """Test changelog report generation."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['report', 'changelog'])

        assert result.exit_code == 0
        assert 'Generating changelog' in result.output

    def test_report_index(self, runner, mock_config):
        """Test tools index report generation."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['report', 'index'])

        assert result.exit_code == 0
        assert 'Generating tools index' in result.output


class TestShowCommand:
    """Tests for the show command."""

    def test_show_nonexistent_tool(self, runner, mock_config):
        """Test show command with nonexistent tool ID."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['show', '999'])

        assert result.exit_code == 0
        assert 'not found' in result.output


class TestUpdateCommand:
    """Tests for the update command."""

    def test_update_no_approved_tools(self, runner, mock_config):
        """Test update command with no approved tools."""
        runner.invoke(main, ['init'])
        result = runner.invoke(main, ['update'])

        assert result.exit_code == 0
        assert 'No approved tools' in result.output


class TestCLIIntegration:
    """Integration tests for CLI workflow."""

    def test_full_demo_workflow(self, runner, mock_config):
        """Test complete workflow: init -> scout -> analyze -> curate."""
        # Initialize
        result = runner.invoke(main, ['init'])
        assert result.exit_code == 0

        # Scout for discoveries
        result = runner.invoke(main, ['scout', 'reddit', '--demo'])
        assert result.exit_code == 0
        assert 'Scout complete' in result.output

        # Analyze discoveries
        result = runner.invoke(main, ['analyze', '--mock'])
        assert result.exit_code == 0

        # Check status
        result = runner.invoke(main, ['status'])
        assert result.exit_code == 0
        assert 'Pipeline Status' in result.output

    def test_multiple_scouts_demo(self, runner, mock_config):
        """Test running multiple scouts."""
        runner.invoke(main, ['init'])

        # Run different scouts
        for scout_name in ['reddit', 'twitter', 'rss']:
            result = runner.invoke(main, ['scout', scout_name, '--demo'])
            assert result.exit_code == 0
            assert 'Scout complete' in result.output
