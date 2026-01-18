"""
Analyzer Base Module

Framework for analyzing discoveries and extracting structured data.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from src.database import Database


@dataclass
class ExtractedTool:
    """A tool extracted from a discovery."""
    name: str
    url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


@dataclass
class ExtractedClaim:
    """A claim extracted about a tool."""
    tool_name: str
    claim_type: str  # feature, pricing, integration, limitation, comparison, use_case
    content: str
    confidence: float = 0.5


@dataclass
class AnalysisResult:
    """Result of analyzing a discovery."""
    discovery_id: int
    tools: list[ExtractedTool] = field(default_factory=list)
    claims: list[ExtractedClaim] = field(default_factory=list)
    raw_response: Optional[str] = None
    error: Optional[str] = None


class Analyzer(ABC):
    """Abstract base class for analyzers."""

    def __init__(self, db: Database, config: Optional[dict] = None):
        self.db = db
        self.config = config or {}

    @abstractmethod
    def analyze(self, discovery: dict) -> AnalysisResult:
        """Analyze a single discovery and extract tools/claims."""
        pass

    def process_discoveries(self, limit: int = 10) -> list[AnalysisResult]:
        """Process unprocessed discoveries."""
        discoveries = self.db.get_unprocessed_discoveries(limit=limit)
        results = []

        for discovery in discoveries:
            result = self.analyze(discovery)
            results.append(result)

            if not result.error:
                self._save_result(result, discovery)

        return results

    def _save_result(self, result: AnalysisResult, discovery: dict):
        """Save extracted tools and claims to database."""
        source_id = discovery['source_id']

        for tool in result.tools:
            # Skip tools without URLs
            if not tool.url:
                continue

            # Add or get existing tool
            tool_id = self.db.add_tool(
                name=tool.name,
                url=tool.url,
                description=tool.description,
                category=tool.category,
                status='analyzing'
            )

            # Add claims for this tool
            for claim in result.claims:
                if claim.tool_name.lower() == tool.name.lower():
                    self.db.add_claim(
                        tool_id=tool_id,
                        source_id=source_id,
                        content=claim.content,
                        claim_type=claim.claim_type,
                        confidence=claim.confidence,
                        raw_text=discovery.get('raw_text', '')[:500]
                    )

        # Mark discovery as processed
        # Link to first tool if any were extracted
        first_tool_id = None
        if result.tools:
            first_tool = self.db.connect().execute(
                "SELECT id FROM tools WHERE name = ?",
                (result.tools[0].name,)
            ).fetchone()
            if first_tool:
                first_tool_id = first_tool[0]

        self.db.mark_discovery_processed(result.discovery_id, first_tool_id)


# Tool categories based on glossary.md
TOOL_CATEGORIES = [
    "prospecting",      # Lead finding, list building
    "enrichment",       # Data enrichment, contact info
    "outreach",         # Email/LinkedIn automation
    "conversation",     # Call recording, conversation intelligence
    "crm",              # CRM systems
    "scheduling",       # Meeting scheduling
    "analytics",        # Sales analytics, forecasting
    "coaching",         # Sales training, coaching
    "other"             # Doesn't fit above
]

CLAIM_TYPES = [
    "feature",          # Product capabilities
    "pricing",          # Cost, plans, tiers
    "integration",      # Connects with other tools
    "limitation",       # What it can't do
    "comparison",       # Compared to competitors
    "use_case",         # How it's used (workflows, applications)
    "audience"          # Target audience (structured JSON)
]
