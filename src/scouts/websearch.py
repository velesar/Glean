"""
Web Search Scout

Discovers AI sales tools through web search engines.

Supports multiple search providers:
1. SerpAPI (Google search results via API)
2. Google Custom Search API
3. Demo mode (sample data for testing)
"""

from typing import Optional
from urllib.parse import urlparse

import httpx

from src.database import Database
from src.scouts.base import Discovery, Scout, extract_urls, is_relevant, rate_limit

# Default search queries for finding AI sales tools
DEFAULT_SEARCH_QUERIES = [
    'best AI tools for sales 2026',
    'AI sales automation software',
    'AI SDR tools review',
    'AI cold email software',
    'AI lead generation tools',
    'sales AI copilot launch',
    'new AI sales tool announcement',
    'AI outreach platform',
]

# Domains to exclude (not useful for tool discovery)
EXCLUDED_DOMAINS = [
    'youtube.com', 'facebook.com', 'linkedin.com', 'twitter.com',
    'reddit.com',  # We have a dedicated Reddit scout
    'quora.com', 'pinterest.com', 'instagram.com',
    'wikipedia.org', 'amazon.com', 'ebay.com',
]


class WebSearchScout(Scout):
    """Scout for web search results about AI sales tools.

    Supports multiple search providers:
    - SerpAPI: Set serpapi.api_key in config
    - Google Custom Search: Set google.api_key and google.cx in config

    Configure in config.yaml under api_keys:
        serpapi:
            api_key: "your_serpapi_key"
        # OR
        google:
            api_key: "your_google_api_key"
            cx: "your_custom_search_engine_id"
    """

    source_name = 'web_search'

    def __init__(self, db: Database, config: dict = None):
        super().__init__(db, config)
        self.search_queries = self.config.get('search_queries', DEFAULT_SEARCH_QUERIES)
        self.results_per_query = self.config.get('results_per_query', 10)
        self.demo_mode = self.config.get('demo', False)

        # Search provider credentials
        self.serpapi_key = self.config.get('serpapi', {}).get('api_key')
        self.google_api_key = self.config.get('google', {}).get('api_key')
        self.google_cx = self.config.get('google', {}).get('cx')

        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    def run(self) -> list[Discovery]:
        """Run the web search scout."""
        if self.demo_mode:
            print("  Running in demo mode with sample data...")
            return self._get_demo_discoveries()

        # Determine which provider to use
        provider = self._get_provider()
        if not provider:
            print("  [!] No search API credentials configured.")
            print("      Configure one of the following in config.yaml:")
            print("        - serpapi.api_key (recommended)")
            print("        - google.api_key and google.cx")
            print("      Or use --demo flag to test with sample data.")
            return []

        print(f"  Using search provider: {provider}")

        all_discoveries = []

        for query in self.search_queries:
            print(f"  Searching: {query[:40]}...")
            try:
                if provider == 'serpapi':
                    discoveries = self._search_serpapi(query)
                else:
                    discoveries = self._search_google(query)

                all_discoveries.extend(discoveries)
                print(f"    Found {len(discoveries)} relevant results")
            except Exception as e:
                print(f"    Error: {e}")

            rate_limit(1.5)  # Be respectful to APIs

        return all_discoveries

    def _get_provider(self) -> Optional[str]:
        """Determine which search provider to use."""
        if self.serpapi_key:
            return 'serpapi'
        elif self.google_api_key and self.google_cx:
            return 'google'
        return None

    def _search_serpapi(self, query: str) -> list[Discovery]:
        """Search using SerpAPI."""
        discoveries = []

        params = {
            'q': query,
            'api_key': self.serpapi_key,
            'num': self.results_per_query,
            'engine': 'google',
        }

        try:
            response = self.client.get(
                'https://serpapi.com/search',
                params=params
            )
            response.raise_for_status()
            data = response.json()

            for result in data.get('organic_results', []):
                discovery = self._result_to_discovery(result, query, 'serpapi')
                if discovery:
                    discoveries.append(discovery)

        except Exception as e:
            print(f"      SerpAPI error: {e}")

        return discoveries

    def _search_google(self, query: str) -> list[Discovery]:
        """Search using Google Custom Search API."""
        discoveries = []

        params = {
            'q': query,
            'key': self.google_api_key,
            'cx': self.google_cx,
            'num': min(self.results_per_query, 10),  # API limit
        }

        try:
            response = self.client.get(
                'https://www.googleapis.com/customsearch/v1',
                params=params
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get('items', []):
                result = {
                    'title': item.get('title'),
                    'link': item.get('link'),
                    'snippet': item.get('snippet'),
                    'displayed_link': item.get('displayLink'),
                }
                discovery = self._result_to_discovery(result, query, 'google')
                if discovery:
                    discoveries.append(discovery)

        except Exception as e:
            print(f"      Google API error: {e}")

        return discoveries

    def _result_to_discovery(self, result: dict, query: str,
                             provider: str) -> Optional[Discovery]:
        """Convert a search result to a Discovery object."""
        url = result.get('link')
        if not url:
            return None

        # Skip excluded domains
        domain = urlparse(url).netloc.lower()
        if any(excluded in domain for excluded in EXCLUDED_DOMAINS):
            return None

        title = result.get('title', '')
        snippet = result.get('snippet', '')
        raw_text = f"{title}\n\n{snippet}".strip()

        # Check relevance
        if not is_relevant(raw_text, min_keywords=1):
            return None

        # Extract any URLs mentioned in the snippet
        urls_in_snippet = extract_urls(snippet)

        return Discovery(
            source_name='web_search',
            source_url=url,
            raw_text=raw_text,
            metadata={
                'type': 'search_result',
                'search_query': query,
                'search_provider': provider,
                'title': title,
                'snippet': snippet,
                'domain': domain,
                'displayed_link': result.get('displayed_link'),
                'position': result.get('position'),
                'urls_mentioned': urls_in_snippet,
            }
        )

    def _get_demo_discoveries(self) -> list[Discovery]:
        """Return sample discoveries for testing."""
        samples = [
            {
                'source_url': 'https://www.techcrunch.com/ai-sales-tools-roundup',
                'raw_text': '''Top 10 AI Sales Tools for 2026 | TechCrunch

The landscape of AI-powered sales tools has exploded this year. From AI SDR
assistants to conversation intelligence platforms, here are the tools that
are changing how sales teams operate. We review Apollo.io, Outreach, Gong,
and several emerging startups.''',
                'metadata': {
                    'type': 'search_result',
                    'search_query': 'best AI tools for sales 2026',
                    'search_provider': 'demo',
                    'title': 'Top 10 AI Sales Tools for 2026',
                    'domain': 'techcrunch.com',
                    'position': 1,
                }
            },
            {
                'source_url': 'https://www.g2.com/categories/ai-sales-assistant',
                'raw_text': '''Best AI Sales Assistant Software in 2026 | G2

Compare the top AI sales assistant software. Read real user reviews and find
the best AI sales assistant for your business. See ratings for features like
email automation, lead scoring, and CRM integration.''',
                'metadata': {
                    'type': 'search_result',
                    'search_query': 'AI sales automation software',
                    'search_provider': 'demo',
                    'title': 'Best AI Sales Assistant Software in 2026',
                    'domain': 'g2.com',
                    'position': 2,
                }
            },
            {
                'source_url': 'https://www.salesforce.com/blog/ai-sales-tools',
                'raw_text': '''How AI is Transforming Sales | Salesforce Blog

Artificial intelligence is revolutionizing the sales process. Einstein GPT
and other AI tools are helping sales teams automate prospecting, personalize
outreach, and close deals faster. Learn how to leverage AI in your sales stack.''',
                'metadata': {
                    'type': 'search_result',
                    'search_query': 'AI SDR tools review',
                    'search_provider': 'demo',
                    'title': 'How AI is Transforming Sales',
                    'domain': 'salesforce.com',
                    'position': 3,
                }
            },
            {
                'source_url': 'https://www.newaisalestool.example.com',
                'raw_text': '''Introducing OutboundAI - The Future of Sales Outreach

We're excited to announce the launch of OutboundAI, a new AI-powered platform
that automates your entire outbound sales process. Using GPT-4, we help SDRs
write personalized emails, find leads, and book meetings on autopilot.''',
                'metadata': {
                    'type': 'search_result',
                    'search_query': 'new AI sales tool announcement',
                    'search_provider': 'demo',
                    'title': 'Introducing OutboundAI - The Future of Sales Outreach',
                    'domain': 'newaisalestool.example.com',
                    'position': 5,
                    'urls_mentioned': ['https://www.newaisalestool.example.com'],
                }
            },
            {
                'source_url': 'https://www.forbes.com/ai-cold-email-tools',
                'raw_text': '''5 AI Tools That Will Transform Your Cold Email Strategy

Cold email is getting a major upgrade thanks to AI. These five tools use
machine learning to improve deliverability, personalization, and response
rates. We tested Lemlist, Instantly, and Woodpecker.''',
                'metadata': {
                    'type': 'search_result',
                    'search_query': 'AI cold email software',
                    'search_provider': 'demo',
                    'title': '5 AI Tools That Will Transform Your Cold Email Strategy',
                    'domain': 'forbes.com',
                    'position': 4,
                }
            },
        ]

        return [
            Discovery(
                source_name='web_search',
                source_url=s['source_url'],
                raw_text=s['raw_text'],
                metadata=s['metadata']
            )
            for s in samples
        ]

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def run_websearch_scout(db: Database, config: dict = None) -> tuple[int, int]:
    """Convenience function to run the web search scout."""
    scout = WebSearchScout(db, config)
    try:
        discoveries = scout.run()
        saved, skipped = scout.save_all(discoveries)
        return saved, skipped
    finally:
        scout.close()
