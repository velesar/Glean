"""
Update Tracker Module

Monitors approved tools for changes and updates.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from src.database import Database


@dataclass
class PageSnapshot:
    """Snapshot of a tool's webpage."""
    url: str
    title: Optional[str]
    content_hash: str
    pricing_text: Optional[str]
    features_text: Optional[str]
    fetched_at: datetime
    error: Optional[str] = None


@dataclass
class DetectedChange:
    """A detected change in a tool."""
    tool_id: int
    tool_name: str
    change_type: str  # pricing_change, feature_added, feature_removed, news, content_change
    description: str
    source_url: Optional[str] = None


# Patterns to extract pricing information
PRICING_PATTERNS = [
    r'\$[\d,]+(?:\.\d{2})?(?:\s*/?(?:mo|month|yr|year|user))?',
    r'(?:free|starter|pro|enterprise|business|team)\s*(?:plan|tier)?',
    r'(?:pricing|plans?|subscription)',
]

# Patterns to extract features
FEATURE_PATTERNS = [
    r'(?:features?|capabilities|includes?):?\s*([^\n.]+)',
    r'(?:✓|✔|•)\s*([^\n]+)',
]


class UpdateTracker:
    """Tracks updates to approved tools."""

    def __init__(self, db: Database, config: Optional[dict] = None):
        self.db = db
        self.config = config or {}
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

    def check_tool(self, tool: dict) -> list[DetectedChange]:
        """Check a single tool for updates."""
        changes: list[DetectedChange] = []
        url = tool.get('url')

        if not url:
            return changes

        # Fetch current page
        snapshot = self._fetch_page(url)
        if snapshot.error:
            return changes

        # Get previous snapshot from database
        previous = self._get_previous_snapshot(tool['id'])

        if previous:
            # Compare and detect changes
            changes = self._detect_changes(tool, previous, snapshot)

        # Store new snapshot
        self._store_snapshot(tool['id'], snapshot)

        return changes

    def check_all_approved(self) -> list[DetectedChange]:
        """Check all approved tools for updates."""
        tools = self.db.get_tools_by_status('approved')
        all_changes = []

        for tool in tools:
            try:
                changes = self.check_tool(tool)
                all_changes.extend(changes)
            except Exception as e:
                print(f"  Error checking {tool['name']}: {e}")

        return all_changes

    def _fetch_page(self, url: str) -> PageSnapshot:
        """Fetch and parse a webpage."""
        try:
            response = self.client.get(url)
            response.raise_for_status()
            html = response.text

            # Extract title
            title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else None

            # Remove script/style tags for cleaner text
            clean_html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)

            # Extract text content
            text = re.sub(r'<[^>]+>', ' ', clean_html)
            text = re.sub(r'\s+', ' ', text).strip()

            # Hash the content (not used for security, just for deduplication)
            content_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()

            # Extract pricing info
            pricing_text = self._extract_pricing(text)

            # Extract features
            features_text = self._extract_features(text)

            return PageSnapshot(
                url=url,
                title=title,
                content_hash=content_hash,
                pricing_text=pricing_text,
                features_text=features_text,
                fetched_at=datetime.now()
            )

        except Exception as e:
            return PageSnapshot(
                url=url,
                title=None,
                content_hash='',
                pricing_text=None,
                features_text=None,
                fetched_at=datetime.now(),
                error=str(e)
            )

    def _extract_pricing(self, text: str) -> Optional[str]:
        """Extract pricing-related text."""
        matches = []
        for pattern in PRICING_PATTERNS:
            found = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found)

        if matches:
            return ' | '.join(set(matches[:10]))  # Limit to 10 unique matches
        return None

    def _extract_features(self, text: str) -> Optional[str]:
        """Extract feature-related text."""
        matches = []
        for pattern in FEATURE_PATTERNS:
            found = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found)

        if matches:
            return ' | '.join(set(matches[:10]))
        return None

    def _get_previous_snapshot(self, tool_id: int) -> Optional[dict]:
        """Get previous snapshot from database."""
        conn = self.db.connect()
        row = conn.execute(
            """SELECT * FROM tool_snapshots
               WHERE tool_id = ?
               ORDER BY fetched_at DESC LIMIT 1""",
            (tool_id,)
        ).fetchone()
        return dict(row) if row else None

    def _store_snapshot(self, tool_id: int, snapshot: PageSnapshot):
        """Store a snapshot in the database."""
        conn = self.db.connect()
        conn.execute(
            """INSERT INTO tool_snapshots
               (tool_id, url, title, content_hash, pricing_text, features_text, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tool_id, snapshot.url, snapshot.title, snapshot.content_hash,
             snapshot.pricing_text, snapshot.features_text, snapshot.fetched_at)
        )
        conn.commit()

    def _detect_changes(self, tool: dict, previous: dict, current: PageSnapshot) -> list[DetectedChange]:
        """Detect changes between snapshots."""
        changes = []
        tool_id = tool['id']
        tool_name = tool['name']

        # Check content hash
        if previous.get('content_hash') and previous['content_hash'] != current.content_hash:
            # Content changed - determine type

            # Check pricing changes
            if previous.get('pricing_text') != current.pricing_text:
                if current.pricing_text and not previous.get('pricing_text'):
                    desc = f"Pricing info added: {current.pricing_text[:100]}"
                elif previous.get('pricing_text') and not current.pricing_text:
                    desc = "Pricing info removed"
                else:
                    desc = f"Pricing updated: {current.pricing_text[:100] if current.pricing_text else 'N/A'}"

                changes.append(DetectedChange(
                    tool_id=tool_id,
                    tool_name=tool_name,
                    change_type='pricing_change',
                    description=desc,
                    source_url=current.url
                ))

            # Check feature changes
            if previous.get('features_text') != current.features_text:
                if current.features_text and not previous.get('features_text'):
                    desc = "Features section added"
                elif previous.get('features_text') and not current.features_text:
                    desc = "Features section changed"
                else:
                    desc = "Features updated"

                changes.append(DetectedChange(
                    tool_id=tool_id,
                    tool_name=tool_name,
                    change_type='feature_added',
                    description=desc,
                    source_url=current.url
                ))

            # General content change if no specific changes detected
            if not changes:
                changes.append(DetectedChange(
                    tool_id=tool_id,
                    tool_name=tool_name,
                    change_type='content_change',
                    description="Website content updated",
                    source_url=current.url
                ))

        # Check title change
        if previous.get('title') and current.title and previous['title'] != current.title:
            changes.append(DetectedChange(
                tool_id=tool_id,
                tool_name=tool_name,
                change_type='news',
                description=f"Title changed: '{current.title[:50]}'",
                source_url=current.url
            ))

        return changes

    def close(self):
        """Close HTTP client."""
        self.client.close()


def run_update_check(db: Database, config: Optional[dict] = None) -> dict:
    """Run update check on all approved tools."""
    tracker = UpdateTracker(db, config)

    try:
        changes = tracker.check_all_approved()

        # Log changes to changelog
        for change in changes:
            db.add_changelog_entry(
                change.tool_id,
                change.change_type,
                change.description,
                change.source_url
            )

        return {
            'tools_checked': len(db.get_tools_by_status('approved')),
            'changes_detected': len(changes),
            'changes': changes
        }
    finally:
        tracker.close()
