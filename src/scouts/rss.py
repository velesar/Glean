"""
RSS Feed Scout

Collects AI sales tool mentions from RSS feeds.

Monitors tech blogs, news sites, and product announcement feeds for
relevant content about AI sales tools.

No API authentication required - just configure feed URLs.
"""

import html
import re
from datetime import datetime, timedelta
from typing import Optional
from xml.etree.ElementTree import Element  # noqa: S405 - used for type hints only

import defusedxml.ElementTree as ET  # noqa: N817
import httpx

from src.database import Database
from src.scouts.base import Discovery, Scout, extract_urls, is_relevant, rate_limit

# Default feeds to monitor
DEFAULT_FEEDS = [
    # Tech news
    {
        'name': 'TechCrunch',
        'url': 'https://techcrunch.com/feed/',
        'category': 'tech_news',
    },
    {
        'name': 'The Verge',
        'url': 'https://www.theverge.com/rss/index.xml',
        'category': 'tech_news',
    },
    {
        'name': 'Hacker News',
        'url': 'https://news.ycombinator.com/rss',
        'category': 'tech_news',
    },
    # AI-specific
    {
        'name': 'AI News',
        'url': 'https://www.artificialintelligence-news.com/feed/',
        'category': 'ai_news',
    },
    # SaaS / Startup
    {
        'name': 'SaaStr',
        'url': 'https://www.saastr.com/feed/',
        'category': 'saas',
    },
    # Product launches
    {
        'name': 'Product Hunt',
        'url': 'https://www.producthunt.com/feed',
        'category': 'launches',
    },
]


class RSSScout(Scout):
    """Scout for RSS feed content about AI sales tools.

    No API authentication required. Configure feeds in config.yaml:
        rss:
            feeds:
                - name: "My Feed"
                  url: "https://example.com/feed.xml"
                  category: "custom"

    Or use the default curated list of tech/AI/SaaS feeds.
    """

    source_name = 'rss'

    def __init__(self, db: Database, config: dict = None):
        super().__init__(db, config)
        self.feeds = self.config.get('feeds', DEFAULT_FEEDS)
        self.max_age_days = self.config.get('max_age_days', 7)
        self.demo_mode = self.config.get('demo', False)

        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={'User-Agent': 'Glean/1.0 RSS Scout'}
        )

    def run(self) -> list[Discovery]:
        """Run the RSS scout across all configured feeds."""
        if self.demo_mode:
            print("  Running in demo mode with sample data...")
            return self._get_demo_discoveries()

        all_discoveries = []

        for feed in self.feeds:
            feed_name = feed.get('name', feed.get('url', 'Unknown'))
            print(f"  Fetching: {feed_name}...")
            try:
                discoveries = self._fetch_feed(feed)
                all_discoveries.extend(discoveries)
                print(f"    Found {len(discoveries)} relevant items")
            except Exception as e:
                print(f"    Error: {e}")

            rate_limit(0.5)

        return all_discoveries

    def _fetch_feed(self, feed: dict) -> list[Discovery]:
        """Fetch and parse an RSS feed."""
        discoveries = []
        url = feed.get('url')
        feed_name = feed.get('name', url)
        category = feed.get('category', 'general')

        try:
            response = self.client.get(url)
            response.raise_for_status()
            content = response.text

            # Parse the feed
            items = self._parse_feed(content)

            cutoff_date = datetime.utcnow() - timedelta(days=self.max_age_days)

            for item in items:
                # Check publication date
                pub_date = item.get('pub_date')
                if pub_date and pub_date < cutoff_date:
                    continue

                # Check relevance
                text = f"{item.get('title', '')} {item.get('description', '')}"
                if not is_relevant(text, min_keywords=2):
                    continue

                discovery = self._item_to_discovery(item, feed_name, category)
                if discovery:
                    discoveries.append(discovery)

        except Exception as e:
            raise Exception(f"Failed to fetch {feed_name}: {e}")

        return discoveries

    def _parse_feed(self, content: str) -> list[dict]:
        """Parse RSS/Atom feed content."""
        items = []

        try:
            root = ET.fromstring(content)

            # Detect feed format
            if root.tag == 'rss' or root.tag.endswith('rss'):
                items = self._parse_rss(root)
            elif 'feed' in root.tag.lower() or root.tag.endswith('}feed'):
                items = self._parse_atom(root)
            else:
                # Try RSS first, then Atom
                items = self._parse_rss(root)
                if not items:
                    items = self._parse_atom(root)

        except ET.ParseError as e:
            raise Exception(f"Failed to parse feed XML: {e}")

        return items

    def _parse_rss(self, root: Element) -> list[dict]:
        """Parse RSS 2.0 format."""
        items = []

        # Find channel/items
        channel = root.find('channel')
        if channel is None:
            channel = root

        for item in channel.findall('item'):
            parsed = {
                'title': self._get_text(item, 'title'),
                'link': self._get_text(item, 'link'),
                'description': self._clean_html(self._get_text(item, 'description')),
                'pub_date': self._parse_date(self._get_text(item, 'pubDate')),
                'author': self._get_text(item, 'author') or self._get_text(item, 'dc:creator'),
                'guid': self._get_text(item, 'guid'),
            }
            if parsed['title'] or parsed['link']:
                items.append(parsed)

        return items

    def _parse_atom(self, root: Element) -> list[dict]:
        """Parse Atom format."""
        items = []

        # Handle namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        entries = root.findall('atom:entry', ns)
        if not entries:
            entries = root.findall('entry')
        if not entries:
            # Try without namespace
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')

        for entry in entries:
            # Get link (may be in href attribute)
            link = None
            link_elem = entry.find('atom:link', ns) or entry.find('link')
            if link_elem is not None:
                link = link_elem.get('href') or link_elem.text

            # Get content/summary
            content = (
                self._get_text_ns(entry, 'content', ns) or
                self._get_text_ns(entry, 'summary', ns) or
                ''
            )

            parsed = {
                'title': self._get_text_ns(entry, 'title', ns),
                'link': link,
                'description': self._clean_html(content),
                'pub_date': self._parse_date(
                    self._get_text_ns(entry, 'published', ns) or
                    self._get_text_ns(entry, 'updated', ns)
                ),
                'author': self._get_text_ns(entry, 'author/name', ns),
                'guid': self._get_text_ns(entry, 'id', ns),
            }
            if parsed['title'] or parsed['link']:
                items.append(parsed)

        return items

    def _get_text(self, element: Element, tag: str) -> Optional[str]:
        """Get text content of a child element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None

    def _get_text_ns(self, element: Element, path: str,
                     ns: dict) -> Optional[str]:
        """Get text with namespace handling."""
        # Try with namespace prefix
        child = element.find(f'atom:{path}', ns)
        if child is None:
            # Try without namespace
            child = element.find(path)
        if child is None:
            # Try with full namespace
            child = element.find(f'{{http://www.w3.org/2005/Atom}}{path}')

        if child is not None:
            return (child.text or '').strip()
        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and decode entities."""
        if not text:
            return ''

        # Decode HTML entities
        text = html.unescape(text)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats found in feeds."""
        if not date_str:
            return None

        # Common formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 822
            '%a, %d %b %Y %H:%M:%S %Z',
            '%Y-%m-%dT%H:%M:%S%z',       # ISO 8601
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]

        # Clean up timezone indicators
        date_str = re.sub(r'\s*\+0000$', ' +0000', date_str)
        date_str = re.sub(r'\s*GMT$', ' +0000', date_str)

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                # Convert to UTC if timezone aware
                if dt.tzinfo:
                    return dt.replace(tzinfo=None)
                return dt
            except ValueError:
                continue

        return None

    def _item_to_discovery(self, item: dict, feed_name: str,
                           category: str) -> Optional[Discovery]:
        """Convert a feed item to a Discovery object."""
        link = item.get('link')
        if not link:
            return None

        title = item.get('title', '')
        description = item.get('description', '')
        raw_text = f"{title}\n\n{description}".strip()

        # Extract URLs from description
        urls_in_text = extract_urls(description)

        return Discovery(
            source_name='rss',
            source_url=link,
            raw_text=raw_text,
            metadata={
                'type': 'feed_item',
                'feed_name': feed_name,
                'feed_category': category,
                'title': title,
                'author': item.get('author'),
                'pub_date': item.get('pub_date').isoformat() if item.get('pub_date') else None,
                'guid': item.get('guid'),
                'urls_mentioned': urls_in_text,
            }
        )

    def _get_demo_discoveries(self) -> list[Discovery]:
        """Return sample discoveries for testing."""
        samples = [
            {
                'source_url': 'https://techcrunch.com/2026/01/10/new-ai-sales-platform',
                'raw_text': '''New AI Sales Platform Raises $50M to Automate Outbound

A new AI-powered sales platform called OutreachBot has raised $50 million in
Series B funding. The platform uses GPT-4 to automate cold email outreach,
prospect research, and meeting scheduling for SDR teams.''',
                'metadata': {
                    'type': 'feed_item',
                    'feed_name': 'TechCrunch',
                    'feed_category': 'tech_news',
                    'title': 'New AI Sales Platform Raises $50M to Automate Outbound',
                    'author': 'Sarah Writer',
                    'pub_date': '2026-01-10T14:30:00',
                }
            },
            {
                'source_url': 'https://news.ycombinator.com/item?id=demo1',
                'raw_text': '''Show HN: I built an AI assistant for sales prospecting

After 5 years as an SDR, I built the tool I always wanted. ProspectGPT uses
AI to find leads, enrich their data, and craft personalized outreach messages.
Looking for feedback from the HN community.''',
                'metadata': {
                    'type': 'feed_item',
                    'feed_name': 'Hacker News',
                    'feed_category': 'tech_news',
                    'title': 'Show HN: I built an AI assistant for sales prospecting',
                    'author': 'hackerfounder',
                    'pub_date': '2026-01-09T10:15:00',
                }
            },
            {
                'source_url': 'https://www.saastr.com/ai-sales-tools-guide',
                'raw_text': '''The Complete Guide to AI Sales Tools in 2026

Everything you need to know about AI in sales. We cover conversation intelligence
(Gong, Chorus), email automation (Outreach, Salesloft), and the new wave of
AI SDR tools. Plus interviews with sales leaders using AI to hit quota.''',
                'metadata': {
                    'type': 'feed_item',
                    'feed_name': 'SaaStr',
                    'feed_category': 'saas',
                    'title': 'The Complete Guide to AI Sales Tools in 2026',
                    'author': 'Jason Lemkin',
                    'pub_date': '2026-01-08T09:00:00',
                }
            },
            {
                'source_url': 'https://www.producthunt.com/posts/salesai',
                'raw_text': '''SalesAI - AI-Powered Sales Automation

SalesAI automates the entire outbound sales process with artificial intelligence.
Features include AI email writing, automated sequences, lead scoring, and
CRM sync. Now in beta - join 500+ companies on the waitlist.''',
                'metadata': {
                    'type': 'feed_item',
                    'feed_name': 'Product Hunt',
                    'feed_category': 'launches',
                    'title': 'SalesAI - AI-Powered Sales Automation',
                    'pub_date': '2026-01-07T12:00:00',
                    'urls_mentioned': ['https://salesai.example.com'],
                }
            },
            {
                'source_url': 'https://www.artificialintelligence-news.com/sales-ai-breakthrough',
                'raw_text': '''Major Breakthrough in AI Sales Technology Announced

Researchers have developed a new AI model specifically trained for B2B sales
conversations. The model outperforms GPT-4 on sales-specific tasks like
objection handling and discovery call analysis. Several vendors planning integration.''',
                'metadata': {
                    'type': 'feed_item',
                    'feed_name': 'AI News',
                    'feed_category': 'ai_news',
                    'title': 'Major Breakthrough in AI Sales Technology Announced',
                    'author': 'AI News Team',
                    'pub_date': '2026-01-06T15:45:00',
                }
            },
        ]

        return [
            Discovery(
                source_name='rss',
                source_url=s['source_url'],
                raw_text=s['raw_text'],
                metadata=s['metadata']
            )
            for s in samples
        ]

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def run_rss_scout(db: Database, config: dict = None) -> tuple[int, int]:
    """Convenience function to run the RSS scout."""
    scout = RSSScout(db, config)
    try:
        discoveries = scout.run()
        saved, skipped = scout.save_all(discoveries)
        return saved, skipped
    finally:
        scout.close()
