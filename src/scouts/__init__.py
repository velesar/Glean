"""
Glean Scouts Module

Data collectors for various sources.
"""

from src.scouts.base import Scout, Discovery, is_relevant, extract_urls
from src.scouts.reddit import RedditScout, run_reddit_scout
from src.scouts.twitter import TwitterScout, run_twitter_scout
from src.scouts.producthunt import ProductHuntScout, run_producthunt_scout
from src.scouts.websearch import WebSearchScout, run_websearch_scout
from src.scouts.rss import RSSScout, run_rss_scout

__all__ = [
    # Base
    'Scout',
    'Discovery',
    'is_relevant',
    'extract_urls',
    # Reddit
    'RedditScout',
    'run_reddit_scout',
    # Twitter/X
    'TwitterScout',
    'run_twitter_scout',
    # Product Hunt
    'ProductHuntScout',
    'run_producthunt_scout',
    # Web Search
    'WebSearchScout',
    'run_websearch_scout',
    # RSS
    'RSSScout',
    'run_rss_scout',
]
