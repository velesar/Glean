"""
Twitter/X Scout

Collects AI sales tool mentions from Twitter/X.

NOTE: Twitter API v2 requires authentication. This scout supports:
1. Authenticated mode (requires Bearer token in config.yaml)
2. Demo mode (uses sample data for testing the pipeline)
"""

import httpx
from datetime import datetime, timedelta
from typing import Optional

from src.scouts.base import (
    Scout, Discovery, is_relevant, extract_urls, rate_limit
)
from src.database import Database


# Search queries for finding AI sales tools
DEFAULT_SEARCH_QUERIES = [
    '"AI sales tool" -is:retweet',
    '"sales automation" AI -is:retweet',
    '"SDR tool" OR "BDR tool" -is:retweet',
    'AI "cold email" -is:retweet',
    '"sales AI" launched OR released OR announcing -is:retweet',
]


class TwitterAuthError(Exception):
    """Raised when Twitter API authentication fails."""
    pass


class TwitterScout(Scout):
    """Scout for Twitter/X posts about AI sales tools.

    Twitter API v2 requires a Bearer token for authentication.
    Configure in config.yaml under api_keys.twitter:
        twitter:
            bearer_token: "your_bearer_token"
    """

    source_name = 'twitter'

    def __init__(self, db: Database, config: dict = None):
        super().__init__(db, config)
        self.search_queries = self.config.get('search_queries', DEFAULT_SEARCH_QUERIES)
        self.max_results = self.config.get('max_results', 100)
        self.min_likes = self.config.get('min_likes', 5)
        self.min_retweets = self.config.get('min_retweets', 2)
        self.demo_mode = self.config.get('demo', False)

        # Twitter API credentials
        twitter_config = self.config.get('twitter', {})
        self.bearer_token = twitter_config.get('bearer_token')

        self.client = httpx.Client(timeout=30.0, follow_redirects=True)
        self.base_url = 'https://api.twitter.com/2'

    def _get_headers(self) -> dict:
        """Get headers for authenticated requests."""
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'User-Agent': 'Glean/1.0',
        }

    def run(self) -> list[Discovery]:
        """Run the Twitter scout across all search queries."""
        if self.demo_mode:
            print("  Running in demo mode with sample data...")
            return self._get_demo_discoveries()

        if not self.bearer_token:
            print("  [!] No Twitter API credentials configured.")
            print("      Twitter API requires a Bearer token.")
            print("      To configure:")
            print("        1. Apply for Twitter API access at https://developer.twitter.com")
            print("        2. Add bearer_token to config.yaml under api_keys.twitter")
            print("      Or use --demo flag to test with sample data.")
            return []

        all_discoveries = []

        for query in self.search_queries:
            print(f"  Searching: {query[:50]}...")
            try:
                discoveries = self._search_tweets(query)
                all_discoveries.extend(discoveries)
                print(f"    Found {len(discoveries)} relevant tweets")
            except TwitterAuthError as e:
                print(f"    [!] Auth error: {e}")
                break
            except Exception as e:
                print(f"    Error: {e}")

            rate_limit(1.0)

        return all_discoveries

    def _search_tweets(self, query: str) -> list[Discovery]:
        """Search for tweets matching a query."""
        discoveries = []

        params = {
            'query': query,
            'max_results': min(self.max_results, 100),  # API limit
            'tweet.fields': 'created_at,public_metrics,author_id,entities',
            'expansions': 'author_id',
            'user.fields': 'username,name,verified',
        }

        try:
            response = self.client.get(
                f'{self.base_url}/tweets/search/recent',
                params=params,
                headers=self._get_headers()
            )

            if response.status_code == 401:
                raise TwitterAuthError("Invalid or expired Bearer token")
            elif response.status_code == 403:
                raise TwitterAuthError("API access forbidden - check your access level")

            response.raise_for_status()
            data = response.json()

            # Build author lookup
            authors = {}
            for user in data.get('includes', {}).get('users', []):
                authors[user['id']] = user

            # Process tweets
            for tweet in data.get('data', []):
                metrics = tweet.get('public_metrics', {})

                # Filter by engagement
                likes = metrics.get('like_count', 0)
                retweets = metrics.get('retweet_count', 0)
                if likes < self.min_likes and retweets < self.min_retweets:
                    continue

                # Check relevance
                if not is_relevant(tweet.get('text', '')):
                    continue

                discovery = self._tweet_to_discovery(tweet, authors)
                if discovery:
                    discoveries.append(discovery)

        except httpx.HTTPStatusError as e:
            print(f"      API error: {e.response.status_code}")

        return discoveries

    def _tweet_to_discovery(self, tweet: dict, authors: dict) -> Optional[Discovery]:
        """Convert a tweet to a Discovery object."""
        tweet_id = tweet.get('id')
        if not tweet_id:
            return None

        text = tweet.get('text', '')
        author_id = tweet.get('author_id')
        author = authors.get(author_id, {})
        username = author.get('username', 'unknown')

        # Extract URLs from tweet
        urls_in_text = extract_urls(text)
        entities = tweet.get('entities', {})
        for url_entity in entities.get('urls', []):
            expanded_url = url_entity.get('expanded_url')
            if expanded_url and 'twitter.com' not in expanded_url:
                urls_in_text.append(expanded_url)

        metrics = tweet.get('public_metrics', {})

        return Discovery(
            source_name='twitter',
            source_url=f"https://twitter.com/{username}/status/{tweet_id}",
            raw_text=text,
            metadata={
                'type': 'tweet',
                'author_username': username,
                'author_name': author.get('name'),
                'author_verified': author.get('verified', False),
                'likes': metrics.get('like_count', 0),
                'retweets': metrics.get('retweet_count', 0),
                'replies': metrics.get('reply_count', 0),
                'created_at': tweet.get('created_at'),
                'urls_mentioned': list(set(urls_in_text)),
            }
        )

    def _get_demo_discoveries(self) -> list[Discovery]:
        """Return sample discoveries for testing."""
        samples = [
            {
                'source_url': 'https://twitter.com/sales_tech_guru/status/demo1',
                'raw_text': '''Just discovered an amazing AI sales tool called SalesGPT - it writes personalized cold emails that actually get responses!

Tested it for a week and saw 3x improvement in reply rates.

Link: https://salesgpt.example.com

#SalesAutomation #AI #SDR''',
                'metadata': {
                    'type': 'tweet',
                    'author_username': 'sales_tech_guru',
                    'author_name': 'Sales Tech Guru',
                    'author_verified': True,
                    'likes': 234,
                    'retweets': 45,
                    'replies': 23,
                    'urls_mentioned': ['https://salesgpt.example.com'],
                }
            },
            {
                'source_url': 'https://twitter.com/startup_founder/status/demo2',
                'raw_text': '''🚀 Excited to announce: We just launched ProspectAI!

AI-powered lead scoring that integrates with Salesforce and HubSpot.

Features:
- GPT-4 powered insights
- Real-time enrichment
- Automated sequences

Try it free: https://prospectai.example.com

#AI #Sales #B2B''',
                'metadata': {
                    'type': 'tweet',
                    'author_username': 'startup_founder',
                    'author_name': 'Jane Startup',
                    'author_verified': False,
                    'likes': 89,
                    'retweets': 23,
                    'replies': 12,
                    'urls_mentioned': ['https://prospectai.example.com'],
                }
            },
            {
                'source_url': 'https://twitter.com/sdr_tips/status/demo3',
                'raw_text': '''Thread: Best AI tools for SDRs in 2026 🧵

1/ Clay - Amazing for data enrichment. The AI features for finding email patterns are 🔥

2/ Instantly - Best for cold email at scale. Their warmup feature is unmatched.

3/ Lavender - Real-time email coaching. My reps improved 40% using it.''',
                'metadata': {
                    'type': 'tweet',
                    'author_username': 'sdr_tips',
                    'author_name': 'SDR Tips',
                    'author_verified': False,
                    'likes': 567,
                    'retweets': 123,
                    'replies': 45,
                    'urls_mentioned': [],
                }
            },
            {
                'source_url': 'https://twitter.com/ai_reviewer/status/demo4',
                'raw_text': '''Comparing Gong vs Chorus for conversation intelligence:

Gong: Better AI insights, pricier
Chorus: Better Salesforce integration

Both use AI to analyze sales calls but Gong's deal intelligence is next level.

Full review: https://aireviews.example.com/gong-vs-chorus''',
                'metadata': {
                    'type': 'tweet',
                    'author_username': 'ai_reviewer',
                    'author_name': 'AI Tool Reviewer',
                    'author_verified': True,
                    'likes': 312,
                    'retweets': 67,
                    'replies': 28,
                    'urls_mentioned': ['https://aireviews.example.com/gong-vs-chorus'],
                }
            },
        ]

        return [
            Discovery(
                source_name='twitter',
                source_url=s['source_url'],
                raw_text=s['raw_text'],
                metadata=s['metadata']
            )
            for s in samples
        ]

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def run_twitter_scout(db: Database, config: dict = None) -> tuple[int, int]:
    """Convenience function to run the Twitter scout."""
    scout = TwitterScout(db, config)
    try:
        discoveries = scout.run()
        saved, skipped = scout.save_all(discoveries)
        return saved, skipped
    finally:
        scout.close()
