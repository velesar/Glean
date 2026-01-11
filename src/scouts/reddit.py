"""
Reddit Scout

Collects AI sales tool mentions from Reddit.

NOTE: As of 2023, Reddit requires API authentication for programmatic access.
This scout supports two modes:
1. Authenticated mode (requires credentials in config.yaml)
2. Demo mode (uses sample data for testing the pipeline)
"""

from typing import Optional

import httpx

from src.database import Database
from src.scouts.base import Discovery, Scout, extract_urls, is_relevant, rate_limit

# Default configuration
DEFAULT_SUBREDDITS = [
    'sales',
    'SaaS',
    'salesforce',
    'startups',
    'Entrepreneur',
    'smallbusiness',
]


class RedditAuthError(Exception):
    """Raised when Reddit API authentication fails."""
    pass


class RedditScout(Scout):
    """Scout for Reddit posts and comments about AI sales tools.

    Reddit now requires OAuth authentication for API access.
    Configure credentials in config.yaml under api_keys.reddit:
        reddit:
            client_id: "your_client_id"
            client_secret: "your_client_secret"
            user_agent: "Glean/1.0"
    """

    source_name = 'reddit'

    def __init__(self, db: Database, config: dict = None):
        super().__init__(db, config)
        self.subreddits = self.config.get('subreddits', DEFAULT_SUBREDDITS)
        self.post_limit = self.config.get('post_limit', 50)
        self.min_score = self.config.get('min_score', 3)
        self.include_comments = self.config.get('include_comments', True)
        self.max_comments_per_post = self.config.get('max_comments_per_post', 20)
        self.demo_mode = self.config.get('demo', False)

        # Check for Reddit credentials
        reddit_config = self.config.get('reddit', {})
        self.client_id = reddit_config.get('client_id')
        self.client_secret = reddit_config.get('client_secret')
        self.user_agent = reddit_config.get('user_agent', 'Glean/1.0')

        self._access_token = None
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    def _authenticate(self) -> bool:
        """Authenticate with Reddit OAuth and get access token."""
        if not self.client_id or not self.client_secret:
            return False

        auth_url = 'https://www.reddit.com/api/v1/access_token'
        try:
            response = self.client.post(
                auth_url,
                auth=(self.client_id, self.client_secret),
                data={'grant_type': 'client_credentials'},
                headers={'User-Agent': self.user_agent}
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data.get('access_token')
            return bool(self._access_token)
        except Exception as e:
            print(f"    Authentication failed: {e}")
            return False

    def _get_headers(self) -> dict:
        """Get headers for authenticated requests."""
        headers = {'User-Agent': self.user_agent}
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        return headers

    def run(self) -> list[Discovery]:
        """Run the Reddit scout across all configured subreddits."""
        # Demo mode - return sample data
        if self.demo_mode:
            print("  Running in demo mode with sample data...")
            return self._get_demo_discoveries()

        # Try to authenticate
        if self.client_id and self.client_secret:
            print("  Authenticating with Reddit API...")
            if not self._authenticate():
                raise RedditAuthError(
                    "Failed to authenticate with Reddit. Check your credentials."
                )
            print("  Authentication successful!")
        else:
            print("  [!] No Reddit credentials configured.")
            print("      Reddit requires API authentication since 2023.")
            print("      To configure:")
            print("        1. Create an app at https://www.reddit.com/prefs/apps")
            print("        2. Add credentials to config.yaml under api_keys.reddit")
            print("      Or use --demo flag to test with sample data.")
            return []

        all_discoveries = []

        for subreddit in self.subreddits:
            print(f"  Scanning r/{subreddit}...")
            try:
                discoveries = self._scan_subreddit(subreddit)
                all_discoveries.extend(discoveries)
                print(f"    Found {len(discoveries)} relevant items")
            except Exception as e:
                print(f"    Error scanning r/{subreddit}: {e}")

            rate_limit(1.0)  # Rate limit between subreddits

        return all_discoveries

    def _scan_subreddit(self, subreddit: str) -> list[Discovery]:
        """Scan a single subreddit for relevant posts and comments."""
        discoveries = []

        # Fetch hot and new posts
        for sort in ['hot', 'new']:
            posts = self._fetch_posts(subreddit, sort)

            for post in posts:
                # Check post relevance
                post_text = f"{post.get('title', '')} {post.get('selftext', '')}"

                if is_relevant(post_text):
                    # Add the post itself
                    discovery = self._post_to_discovery(post, subreddit)
                    if discovery:
                        discoveries.append(discovery)

                    # Fetch and check comments if enabled
                    if self.include_comments:
                        rate_limit(0.5)
                        comments = self._fetch_comments(subreddit, post['id'])
                        for comment in comments[:self.max_comments_per_post]:
                            if is_relevant(comment.get('body', '')):
                                cd = self._comment_to_discovery(comment, post, subreddit)
                                if cd:
                                    discoveries.append(cd)

        return discoveries

    def _fetch_posts(self, subreddit: str, sort: str = 'hot') -> list[dict]:
        """Fetch posts from a subreddit using OAuth API."""
        url = f'https://oauth.reddit.com/r/{subreddit}/{sort}'
        params = {'limit': self.post_limit, 'raw_json': 1}

        try:
            response = self.client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()

            posts = []
            for child in data.get('data', {}).get('children', []):
                post = child.get('data', {})
                # Filter by score
                if post.get('score', 0) >= self.min_score:
                    posts.append(post)

            return posts

        except Exception as e:
            print(f"      Error fetching {sort} posts: {e}")
            return []

    def _fetch_comments(self, subreddit: str, post_id: str) -> list[dict]:
        """Fetch comments for a post."""
        url = f'https://oauth.reddit.com/r/{subreddit}/comments/{post_id}'
        params = {'limit': 100, 'raw_json': 1}

        try:
            response = self.client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()

            # Comments are in the second element of the response
            if len(data) < 2:
                return []

            comments = []
            self._extract_comments(data[1].get('data', {}).get('children', []), comments)
            return comments

        except Exception as e:
            print(f"      Error fetching comments: {e}")
            return []

    def _extract_comments(self, children: list, results: list, depth: int = 0):
        """Recursively extract comments from nested structure."""
        if depth > 5:  # Don't go too deep
            return

        for child in children:
            if child.get('kind') != 't1':  # t1 = comment
                continue

            comment = child.get('data', {})
            if comment.get('score', 0) >= self.min_score:
                results.append(comment)

            # Recurse into replies
            replies = comment.get('replies')
            if isinstance(replies, dict):
                reply_children = replies.get('data', {}).get('children', [])
                self._extract_comments(reply_children, results, depth + 1)

    def _post_to_discovery(self, post: dict, subreddit: str) -> Optional[Discovery]:
        """Convert a Reddit post to a Discovery object."""
        post_id = post.get('id')
        if not post_id:
            return None

        title = post.get('title', '')
        selftext = post.get('selftext', '')
        raw_text = f"{title}\n\n{selftext}".strip()

        # Extract URLs mentioned in the post
        urls_in_text = extract_urls(raw_text)
        external_url = post.get('url', '')
        if external_url and not external_url.startswith('https://www.reddit.com'):
            urls_in_text.append(external_url)

        return Discovery(
            source_name='reddit',
            source_url=f"https://www.reddit.com/r/{subreddit}/comments/{post_id}",
            raw_text=raw_text,
            metadata={
                'type': 'post',
                'subreddit': subreddit,
                'author': post.get('author'),
                'score': post.get('score'),
                'num_comments': post.get('num_comments'),
                'created_utc': post.get('created_utc'),
                'urls_mentioned': urls_in_text,
                'is_self': post.get('is_self', True),
            }
        )

    def _comment_to_discovery(self, comment: dict, parent_post: dict,
                               subreddit: str) -> Optional[Discovery]:
        """Convert a Reddit comment to a Discovery object."""
        comment_id = comment.get('id')
        post_id = parent_post.get('id')
        if not comment_id or not post_id:
            return None

        body = comment.get('body', '')
        urls_in_text = extract_urls(body)

        return Discovery(
            source_name='reddit',
            source_url=f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/_/{comment_id}",
            raw_text=body,
            metadata={
                'type': 'comment',
                'subreddit': subreddit,
                'author': comment.get('author'),
                'score': comment.get('score'),
                'created_utc': comment.get('created_utc'),
                'parent_post_id': post_id,
                'parent_post_title': parent_post.get('title'),
                'urls_mentioned': urls_in_text,
            }
        )

    def _get_demo_discoveries(self) -> list[Discovery]:
        """Return sample discoveries for testing the pipeline."""
        samples = [
            {
                'source_url': 'https://www.reddit.com/r/sales/comments/demo1',
                'raw_text': '''Best AI tools for SDR outreach in 2026?

I'm looking for AI-powered tools to help automate my cold email sequences.
Currently using Apollo.io but wondering if there are better alternatives.

Has anyone tried:
- Lavender.ai for email writing
- Instantly.ai for cold outreach
- Clay for data enrichment

Would love recommendations! Our team does about 500 emails/day.''',
                'metadata': {
                    'type': 'post',
                    'subreddit': 'sales',
                    'author': 'demo_user',
                    'score': 45,
                    'num_comments': 23,
                    'urls_mentioned': ['https://apollo.io', 'https://lavender.ai', 'https://instantly.ai'],
                }
            },
            {
                'source_url': 'https://www.reddit.com/r/sales/comments/demo1/_/comment1',
                'raw_text': '''I switched from Apollo to Outreach.io last month and the AI features are incredible.
The sentiment analysis alone has improved our response rates by 30%.

Also check out Gong.io for conversation intelligence - it's a game changer for coaching.''',
                'metadata': {
                    'type': 'comment',
                    'subreddit': 'sales',
                    'author': 'helpful_commenter',
                    'score': 28,
                    'urls_mentioned': ['https://outreach.io', 'https://gong.io'],
                }
            },
            {
                'source_url': 'https://www.reddit.com/r/SaaS/comments/demo2',
                'raw_text': '''Launched our AI sales copilot - would love feedback

Hey r/SaaS! We just launched SalesBot AI (https://salesbot.example.com),
an AI assistant that helps SDRs write personalized emails and LinkedIn messages.

Key features:
- Integrates with your CRM (Salesforce, HubSpot)
- Uses GPT-4 for personalization
- Automatic lead scoring
- A/B testing built in

Free trial available. Roast us!''',
                'metadata': {
                    'type': 'post',
                    'subreddit': 'SaaS',
                    'author': 'startup_founder',
                    'score': 12,
                    'num_comments': 8,
                    'urls_mentioned': ['https://salesbot.example.com'],
                }
            },
            {
                'source_url': 'https://www.reddit.com/r/sales/comments/demo3',
                'raw_text': '''Comparison: AI tools for lead generation 2026

Just spent a month testing various AI lead gen tools. Here's my breakdown:

**Data Enrichment:**
- ZoomInfo: Enterprise, expensive but accurate
- Clay: Modern, great API, reasonable pricing
- Apollo: Good for small teams

**Email Automation:**
- Lemlist: Great for personalization
- Woodpecker: Solid deliverability
- Instantly: Best value for volume

**Conversation Intelligence:**
- Gong: Market leader
- Chorus (ZoomInfo): Good Salesforce integration
- Fireflies: Budget option

Happy to answer questions!''',
                'metadata': {
                    'type': 'post',
                    'subreddit': 'sales',
                    'author': 'sales_ops_manager',
                    'score': 156,
                    'num_comments': 47,
                    'urls_mentioned': [],
                }
            },
        ]

        return [
            Discovery(
                source_name='reddit',
                source_url=s['source_url'],
                raw_text=s['raw_text'],
                metadata=s['metadata']
            )
            for s in samples
        ]

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def run_reddit_scout(db: Database, config: dict = None) -> tuple[int, int]:
    """Convenience function to run the Reddit scout."""
    scout = RedditScout(db, config)
    try:
        discoveries = scout.run()
        saved, skipped = scout.save_all(discoveries)
        return saved, skipped
    finally:
        scout.close()
