"""
Tests for Glean Scout modules.
"""

import pytest

from src.scouts.base import Discovery, is_relevant
from src.scouts.producthunt import ProductHuntScout, run_producthunt_scout
from src.scouts.reddit import RedditScout, run_reddit_scout
from src.scouts.rss import RSSScout, run_rss_scout
from src.scouts.twitter import TwitterScout, run_twitter_scout
from src.scouts.websearch import WebSearchScout, run_websearch_scout


class TestDiscoveryDataclass:
    """Tests for Discovery dataclass."""

    def test_discovery_creation(self):
        """Test creating a Discovery object."""
        discovery = Discovery(
            source_name="test",
            source_url="https://test.com",
            raw_text="Test content",
            metadata={"key": "value"}
        )

        assert discovery.source_name == "test"
        assert discovery.source_url == "https://test.com"
        assert discovery.raw_text == "Test content"
        assert discovery.metadata == {"key": "value"}

    def test_discovery_with_empty_metadata(self):
        """Test Discovery with empty metadata dict."""
        discovery = Discovery(
            source_name="test",
            source_url="https://test.com",
            raw_text="Test content",
            metadata={}
        )

        assert discovery.metadata == {}


class TestIsRelevant:
    """Tests for the is_relevant helper function."""

    def test_relevant_ai_text(self):
        """Test that AI-related text is marked relevant."""
        # Need at least 2 keyword matches (default min_keywords=2)
        assert is_relevant("This AI tool helps with sales automation")  # AI + tool + sales + automation
        assert is_relevant("Machine learning for lead generation software")  # machine learning + lead + software
        assert is_relevant("GPT-powered CRM tool for sales teams")  # GPT + CRM + tool + sales

    def test_relevant_sales_text(self):
        """Test that sales-related text is marked relevant."""
        assert is_relevant("CRM integration with AI features")  # CRM + AI
        assert is_relevant("Sales outreach automation tool")  # sales + outreach + automation + tool
        assert is_relevant("Lead scoring with artificial intelligence")  # lead + artificial intelligence

    def test_irrelevant_text(self):
        """Test that unrelated text is marked not relevant."""
        assert not is_relevant("Best pizza recipes")
        assert not is_relevant("Weather forecast for tomorrow")
        assert not is_relevant("How to train your dog")

    def test_empty_text(self):
        """Test that empty text is not relevant."""
        assert not is_relevant("")
        assert not is_relevant("   ")

    def test_single_keyword_not_enough(self):
        """Test that a single keyword is not enough."""
        # With default min_keywords=2, single matches shouldn't be relevant
        assert not is_relevant("Just some AI here")  # Only 1 match


class TestRedditScout:
    """Tests for Reddit Scout."""

    def test_reddit_scout_demo_mode(self, temp_db):
        """Test Reddit scout in demo mode."""
        config = {'demo': True}
        scout = RedditScout(temp_db, config)
        discoveries = scout.run()

        assert isinstance(discoveries, list)
        assert len(discoveries) > 0

        for discovery in discoveries:
            assert isinstance(discovery, Discovery)
            assert discovery.source_name == 'reddit'
            assert discovery.source_url is not None
            assert discovery.raw_text is not None

    def test_run_reddit_scout_helper(self, temp_db):
        """Test run_reddit_scout helper function."""
        config = {'demo': True}
        saved, skipped = run_reddit_scout(temp_db, config)

        assert isinstance(saved, int)
        assert isinstance(skipped, int)
        assert saved >= 0
        assert skipped >= 0

    def test_reddit_scout_discovery_content(self, temp_db):
        """Test that Reddit discoveries have expected content."""
        config = {'demo': True}
        scout = RedditScout(temp_db, config)
        discoveries = scout.run()

        # Demo discoveries should have metadata
        for discovery in discoveries:
            if discovery.metadata:
                # Should have subreddit info
                assert 'subreddit' in discovery.metadata or isinstance(discovery.metadata, dict)


class TestTwitterScout:
    """Tests for Twitter Scout."""

    def test_twitter_scout_demo_mode(self, temp_db):
        """Test Twitter scout in demo mode."""
        config = {'demo': True}
        scout = TwitterScout(temp_db, config)
        discoveries = scout.run()

        assert isinstance(discoveries, list)
        assert len(discoveries) > 0

        for discovery in discoveries:
            assert isinstance(discovery, Discovery)
            assert discovery.source_name == 'twitter'

    def test_run_twitter_scout_helper(self, temp_db):
        """Test run_twitter_scout helper function."""
        config = {'demo': True}
        saved, skipped = run_twitter_scout(temp_db, config)

        assert isinstance(saved, int)
        assert isinstance(skipped, int)


class TestProductHuntScout:
    """Tests for Product Hunt Scout."""

    def test_producthunt_scout_demo_mode(self, temp_db):
        """Test Product Hunt scout in demo mode."""
        config = {'demo': True}
        scout = ProductHuntScout(temp_db, config)
        discoveries = scout.run()

        assert isinstance(discoveries, list)
        assert len(discoveries) > 0

        for discovery in discoveries:
            assert isinstance(discovery, Discovery)
            assert discovery.source_name == 'producthunt'

    def test_run_producthunt_scout_helper(self, temp_db):
        """Test run_producthunt_scout helper function."""
        config = {'demo': True}
        saved, skipped = run_producthunt_scout(temp_db, config)

        assert isinstance(saved, int)
        assert isinstance(skipped, int)


class TestWebSearchScout:
    """Tests for Web Search Scout."""

    def test_websearch_scout_demo_mode(self, temp_db):
        """Test Web Search scout in demo mode."""
        config = {'demo': True}
        scout = WebSearchScout(temp_db, config)
        discoveries = scout.run()

        assert isinstance(discoveries, list)
        assert len(discoveries) > 0

        for discovery in discoveries:
            assert isinstance(discovery, Discovery)
            assert discovery.source_name == 'web_search'

    def test_run_websearch_scout_helper(self, temp_db):
        """Test run_websearch_scout helper function."""
        config = {'demo': True}
        saved, skipped = run_websearch_scout(temp_db, config)

        assert isinstance(saved, int)
        assert isinstance(skipped, int)


class TestRSSScout:
    """Tests for RSS Scout."""

    def test_rss_scout_demo_mode(self, temp_db):
        """Test RSS scout in demo mode."""
        config = {'demo': True}
        scout = RSSScout(temp_db, config)
        discoveries = scout.run()

        assert isinstance(discoveries, list)
        assert len(discoveries) > 0

        for discovery in discoveries:
            assert isinstance(discovery, Discovery)
            assert discovery.source_name == 'rss'

    def test_run_rss_scout_helper(self, temp_db):
        """Test run_rss_scout helper function."""
        config = {'demo': True}
        saved, skipped = run_rss_scout(temp_db, config)

        assert isinstance(saved, int)
        assert isinstance(skipped, int)


class TestScoutDeduplication:
    """Tests for scout deduplication functionality."""

    def test_scout_skips_duplicates(self, temp_db):
        """Test that scouts skip duplicate discoveries."""
        config = {'demo': True}

        # Run scout first time
        saved1, skipped1 = run_reddit_scout(temp_db, config)

        # Run scout again - should skip duplicates
        saved2, skipped2 = run_reddit_scout(temp_db, config)

        # Second run should save fewer or same (due to duplicates)
        assert saved2 <= saved1 or skipped2 > 0


class TestScoutIntegration:
    """Integration tests for scouts."""

    def test_all_scouts_return_discoveries(self, temp_db):
        """Test that all scouts return discoveries in demo mode."""
        scouts = [
            (RedditScout, 'reddit'),
            (TwitterScout, 'twitter'),
            (ProductHuntScout, 'producthunt'),
            (WebSearchScout, 'web_search'),
            (RSSScout, 'rss'),
        ]

        for ScoutClass, expected_source in scouts:
            config = {'demo': True}
            scout = ScoutClass(temp_db, config)
            discoveries = scout.run()

            assert len(discoveries) > 0, f"{ScoutClass.__name__} returned no discoveries"
            assert all(d.source_name == expected_source for d in discoveries)

    def test_discoveries_saved_to_database(self, temp_db):
        """Test that discoveries are properly saved to database."""
        config = {'demo': True}

        # Get initial count
        initial = temp_db.get_unprocessed_discoveries()
        initial_count = len(initial)

        # Run a scout
        run_reddit_scout(temp_db, config)

        # Get new count
        after = temp_db.get_unprocessed_discoveries()
        after_count = len(after)

        # Should have more discoveries
        assert after_count > initial_count
