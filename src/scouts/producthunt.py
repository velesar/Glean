"""
Product Hunt Scout

Collects AI sales tool launches from Product Hunt.

NOTE: Product Hunt API requires OAuth authentication. This scout supports:
1. Authenticated mode (requires API credentials in config.yaml)
2. Demo mode (uses sample data for testing the pipeline)
"""

from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from src.database import Database
from src.scouts.base import Discovery, Scout

# Categories and topics to search
DEFAULT_TOPICS = [
    'artificial-intelligence',
    'sales',
    'saas',
    'marketing-automation',
    'email',
    'crm',
    'productivity',
]

# Keywords to filter products
SALES_AI_KEYWORDS = [
    'sales', 'sdr', 'bdr', 'outreach', 'prospecting', 'lead',
    'cold email', 'crm', 'automation', 'ai', 'gpt', 'llm',
]


class ProductHuntAuthError(Exception):
    """Raised when Product Hunt API authentication fails."""
    pass


class ProductHuntScout(Scout):
    """Scout for Product Hunt launches related to AI sales tools.

    Product Hunt API requires OAuth credentials.
    Configure in config.yaml under api_keys.producthunt:
        producthunt:
            api_key: "your_api_key"
            api_secret: "your_api_secret"
    """

    source_name = 'producthunt'

    def __init__(self, db: Database, config: Optional[dict] = None):
        super().__init__(db, config)
        self.topics = self.config.get('topics', DEFAULT_TOPICS)
        self.days_back = self.config.get('days_back', 7)
        self.min_votes = self.config.get('min_votes', 10)
        self.demo_mode = self.config.get('demo', False)

        # Product Hunt API credentials
        ph_config = self.config.get('producthunt', {})
        self.api_key = ph_config.get('api_key')
        self.api_secret = ph_config.get('api_secret')

        self._access_token = None
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)
        self.api_url = 'https://api.producthunt.com/v2/api/graphql'

    def _authenticate(self) -> bool:
        """Get OAuth access token."""
        if not self.api_key or not self.api_secret:
            return False

        try:
            response = self.client.post(
                'https://api.producthunt.com/v2/oauth/token',
                json={
                    'client_id': self.api_key,
                    'client_secret': self.api_secret,
                    'grant_type': 'client_credentials',
                }
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
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        return headers

    def run(self) -> list[Discovery]:
        """Run the Product Hunt scout."""
        if self.demo_mode:
            print("  Running in demo mode with sample data...")
            return self._get_demo_discoveries()

        if not self.api_key or not self.api_secret:
            print("  [!] No Product Hunt API credentials configured.")
            print("      Product Hunt API requires OAuth authentication.")
            print("      To configure:")
            print("        1. Register an app at https://api.producthunt.com/v2/oauth/applications")
            print("        2. Add api_key and api_secret to config.yaml under api_keys.producthunt")
            print("      Or use --demo flag to test with sample data.")
            return []

        print("  Authenticating with Product Hunt API...")
        if not self._authenticate():
            raise ProductHuntAuthError("Failed to authenticate with Product Hunt")
        print("  Authentication successful!")

        all_discoveries = []

        # Fetch recent posts
        print(f"  Fetching posts from the last {self.days_back} days...")
        try:
            discoveries = self._fetch_recent_posts()
            all_discoveries.extend(discoveries)
            print(f"    Found {len(discoveries)} relevant products")
        except Exception as e:
            print(f"    Error fetching posts: {e}")

        return all_discoveries

    def _fetch_recent_posts(self) -> list[Discovery]:
        """Fetch recent Product Hunt posts using GraphQL."""
        discoveries = []

        # GraphQL query for recent posts
        query = """
        query GetPosts($first: Int!, $postedAfter: DateTime) {
            posts(first: $first, postedAfter: $postedAfter) {
                edges {
                    node {
                        id
                        name
                        tagline
                        description
                        url
                        website
                        votesCount
                        commentsCount
                        createdAt
                        topics {
                            edges {
                                node {
                                    name
                                    slug
                                }
                            }
                        }
                        makers {
                            name
                            username
                        }
                    }
                }
            }
        }
        """

        posted_after = (datetime.utcnow() - timedelta(days=self.days_back)).isoformat() + 'Z'

        try:
            response = self.client.post(
                self.api_url,
                headers=self._get_headers(),
                json={
                    'query': query,
                    'variables': {
                        'first': 100,
                        'postedAfter': posted_after,
                    }
                }
            )

            if response.status_code == 401:
                raise ProductHuntAuthError("Invalid or expired access token")

            response.raise_for_status()
            data = response.json()

            posts = data.get('data', {}).get('posts', {}).get('edges', [])

            for edge in posts:
                post = edge.get('node', {})

                # Filter by votes
                if post.get('votesCount', 0) < self.min_votes:
                    continue

                # Check if relevant to sales/AI
                if not self._is_sales_ai_relevant(post):
                    continue

                discovery = self._post_to_discovery(post)
                if discovery:
                    discoveries.append(discovery)

        except httpx.HTTPStatusError as e:
            print(f"      API error: {e.response.status_code}")

        return discoveries

    def _is_sales_ai_relevant(self, post: dict) -> bool:
        """Check if a Product Hunt post is relevant to AI sales tools."""
        # Combine text fields for checking
        text = ' '.join([
            post.get('name', ''),
            post.get('tagline', ''),
            post.get('description', ''),
        ]).lower()

        # Check topics
        topics = [
            t['node']['slug']
            for t in post.get('topics', {}).get('edges', [])
        ]

        # Must have at least one relevant topic
        relevant_topics = set(topics) & set(DEFAULT_TOPICS)
        if not relevant_topics:
            return False

        # Check for sales/AI keywords
        keyword_matches = sum(1 for kw in SALES_AI_KEYWORDS if kw in text)
        return keyword_matches >= 2

    def _post_to_discovery(self, post: dict) -> Optional[Discovery]:
        """Convert a Product Hunt post to a Discovery object."""
        post_id = post.get('id')
        if not post_id:
            return None

        name = post.get('name', '')
        tagline = post.get('tagline', '')
        description = post.get('description', '')

        raw_text = f"{name}\n\n{tagline}\n\n{description}".strip()

        topics = [
            t['node']['name']
            for t in post.get('topics', {}).get('edges', [])
        ]

        makers = [
            {'name': m.get('name'), 'username': m.get('username')}
            for m in post.get('makers', [])
        ]

        return Discovery(
            source_name='producthunt',
            source_url=post.get('url', f'https://www.producthunt.com/posts/{post_id}'),
            raw_text=raw_text,
            metadata={
                'type': 'product_launch',
                'product_name': name,
                'tagline': tagline,
                'website': post.get('website'),
                'votes': post.get('votesCount', 0),
                'comments': post.get('commentsCount', 0),
                'topics': topics,
                'makers': makers,
                'created_at': post.get('createdAt'),
                'urls_mentioned': [post.get('website')] if post.get('website') else [],
            }
        )

    def _get_demo_discoveries(self) -> list[Discovery]:
        """Return sample discoveries for testing."""
        samples: list[dict[str, Any]] = [
            {
                'source_url': 'https://www.producthunt.com/posts/salesai-copilot',
                'raw_text': '''SalesAI Copilot

Your AI-powered sales assistant that never sleeps

SalesAI Copilot uses GPT-4 to help SDRs write personalized outreach emails,
research prospects, and manage follow-ups. Integrates with Salesforce, HubSpot,
and all major CRMs. Join 1000+ sales teams already using it.''',
                'metadata': {
                    'type': 'product_launch',
                    'product_name': 'SalesAI Copilot',
                    'tagline': 'Your AI-powered sales assistant that never sleeps',
                    'website': 'https://salesaicopilot.example.com',
                    'votes': 456,
                    'comments': 89,
                    'topics': ['Artificial Intelligence', 'Sales', 'SaaS'],
                    'makers': [{'name': 'John Maker', 'username': 'johnmaker'}],
                    'urls_mentioned': ['https://salesaicopilot.example.com'],
                }
            },
            {
                'source_url': 'https://www.producthunt.com/posts/leadgen-ai',
                'raw_text': '''LeadGen AI

Find and qualify leads automatically with AI

Stop spending hours on prospecting. LeadGen AI uses machine learning to find
your ideal customers, enrich their data, and score them based on buying intent.
Seamless integration with your existing sales stack.''',
                'metadata': {
                    'type': 'product_launch',
                    'product_name': 'LeadGen AI',
                    'tagline': 'Find and qualify leads automatically with AI',
                    'website': 'https://leadgenai.example.com',
                    'votes': 234,
                    'comments': 45,
                    'topics': ['Artificial Intelligence', 'Sales', 'Marketing Automation'],
                    'makers': [{'name': 'Sarah Builder', 'username': 'sarahbuilds'}],
                    'urls_mentioned': ['https://leadgenai.example.com'],
                }
            },
            {
                'source_url': 'https://www.producthunt.com/posts/cold-email-wizard',
                'raw_text': '''Cold Email Wizard

AI writes cold emails that actually get replies

Tired of low response rates? Cold Email Wizard analyzes thousands of successful
cold emails and uses AI to craft personalized messages that convert. Built-in
A/B testing and deliverability optimization included.''',
                'metadata': {
                    'type': 'product_launch',
                    'product_name': 'Cold Email Wizard',
                    'tagline': 'AI writes cold emails that actually get replies',
                    'website': 'https://coldemailwizard.example.com',
                    'votes': 567,
                    'comments': 112,
                    'topics': ['Email', 'Sales', 'Artificial Intelligence'],
                    'makers': [{'name': 'Mike Email', 'username': 'mikeemail'}],
                    'urls_mentioned': ['https://coldemailwizard.example.com'],
                }
            },
            {
                'source_url': 'https://www.producthunt.com/posts/deal-intelligence',
                'raw_text': '''Deal Intelligence

AI-powered deal insights for sales teams

Know exactly which deals will close and which need attention. Deal Intelligence
analyzes your CRM data, emails, and calls to predict deal outcomes and recommend
next best actions. Gong + Salesforce integration available.''',
                'metadata': {
                    'type': 'product_launch',
                    'product_name': 'Deal Intelligence',
                    'tagline': 'AI-powered deal insights for sales teams',
                    'website': 'https://dealintel.example.com',
                    'votes': 345,
                    'comments': 67,
                    'topics': ['CRM', 'Artificial Intelligence', 'Sales'],
                    'makers': [{'name': 'Lisa Data', 'username': 'lisadata'}],
                    'urls_mentioned': ['https://dealintel.example.com'],
                }
            },
        ]

        return [
            Discovery(
                source_name='producthunt',
                source_url=s['source_url'],
                raw_text=s['raw_text'],
                metadata=s['metadata']
            )
            for s in samples
        ]

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def run_producthunt_scout(db: Database, config: Optional[dict] = None) -> tuple[int, int]:
    """Convenience function to run the Product Hunt scout."""
    scout = ProductHuntScout(db, config)
    try:
        discoveries = scout.run()
        saved, skipped = scout.save_all(discoveries)
        return saved, skipped
    finally:
        scout.close()
