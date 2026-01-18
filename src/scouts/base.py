"""
Scout Base Class

Abstract base for all data collection scouts.
"""

import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from src.database import Database


@dataclass
class Discovery:
    """A raw discovery from a scout."""
    source_name: str
    source_url: str
    raw_text: str
    metadata: dict


class Scout(ABC):
    """Abstract base class for scouts."""

    def __init__(self, db: Database, config: Optional[dict] = None):
        self.db = db
        self.config = config or {}
        self._source_id: Optional[int] = None

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of this scout's source (e.g., 'reddit')."""
        pass

    @property
    def source_id(self) -> int:
        """Get or create the source ID for this scout."""
        if self._source_id is None:
            source = self.db.get_source_by_name(self.source_name)
            if source:
                self._source_id = source['id']
            else:
                raise ValueError(f"Source '{self.source_name}' not found in database")
        return self._source_id

    @abstractmethod
    def run(self) -> list[Discovery]:
        """Run the scout and return discoveries."""
        pass

    def save_discovery(self, discovery: Discovery) -> Optional[int]:
        """Save a discovery to the database, with deduplication."""
        # Check if this URL is already in discoveries
        conn = self.db.connect()
        existing = conn.execute(
            "SELECT id FROM discoveries WHERE source_url = ?",
            (discovery.source_url,)
        ).fetchone()

        if existing:
            return None  # Already have this

        # Save new discovery
        discovery_id = self.db.add_discovery(
            source_id=self.source_id,
            source_url=discovery.source_url,
            raw_text=discovery.raw_text,
            metadata=discovery.metadata
        )
        return discovery_id

    def save_all(self, discoveries: list[Discovery]) -> tuple[int, int]:
        """Save all discoveries, return (saved, skipped) counts."""
        saved = 0
        skipped = 0
        for d in discoveries:
            if self.save_discovery(d):
                saved += 1
            else:
                skipped += 1
        return saved, skipped


# --- Utility Functions ---

# Keywords that suggest AI/sales tool discussion
TOOL_KEYWORDS = [
    # AI terms
    r'\bAI\b', r'\bartificial intelligence\b', r'\bGPT\b', r'\bLLM\b',
    r'\bmachine learning\b', r'\bautomation\b', r'\bautomate\b',
    # Sales terms
    r'\bSDR\b', r'\bBDR\b', r'\bsales\s+automation\b', r'\boutreach\b',
    r'\bprospecting\b', r'\blead\s+gen\b', r'\bleads?\b', r'\bCRM\b',
    r'\bcold\s+email\b', r'\bcold\s+call\b', r'\bsequence\b',
    # Tool indicators
    r'\btool\b', r'\bsoftware\b', r'\bplatform\b', r'\bapp\b',
    r'\bservice\b', r'\bSaaS\b', r'\bproduct\b',
    # Recommendation patterns
    r'recommend', r'suggest', r'looking for', r'what do you use',
    r'anyone use', r'has anyone tried', r'thoughts on', r'review',
    r'alternative to', r'vs\.?\s+', r'compared to',
]

TOOL_PATTERN = re.compile('|'.join(TOOL_KEYWORDS), re.IGNORECASE)


def is_relevant(text: str, min_keywords: int = 2) -> bool:
    """Check if text is likely relevant to AI sales tools."""
    if not text:
        return False
    matches = TOOL_PATTERN.findall(text)
    return len(matches) >= min_keywords


# URL extraction pattern
URL_PATTERN = re.compile(
    r'https?://[^\s<>\[\]()"\'\`]+',
    re.IGNORECASE
)


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    if not text:
        return []
    urls = URL_PATTERN.findall(text)
    # Clean trailing punctuation
    cleaned = []
    for url in urls:
        url = url.rstrip('.,;:!?)\'\"')
        if url and not url.endswith('/'):
            cleaned.append(url)
        elif url:
            cleaned.append(url)
    return list(set(cleaned))


def rate_limit(seconds: float = 1.0):
    """Simple rate limiter - sleep between requests."""
    time.sleep(seconds)
