"""
Claude Analyzer

Uses Claude API to extract tools and claims from discoveries.
"""

import json
import re

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from src.analyzers.base import (
    CLAIM_TYPES,
    TOOL_CATEGORIES,
    AnalysisResult,
    Analyzer,
    ExtractedClaim,
    ExtractedTool,
)
from src.database import Database

EXTRACTION_PROMPT = '''You are analyzing a social media post/comment about AI sales tools.
Extract any AI/software tools mentioned and claims made about them.

POST CONTENT:
{content}

SOURCE INFO:
- Source: {source_name}
- URL: {source_url}
- Score/upvotes: {score}

INSTRUCTIONS:
1. Identify all AI tools, software products, or SaaS platforms mentioned
2. For each tool, extract any claims made about it
3. Assign confidence scores based on:
   - Direct experience claims (high: 0.8-1.0)
   - Secondhand recommendations (medium: 0.5-0.7)
   - Vague mentions (low: 0.2-0.4)

CATEGORIES for tools: {categories}
CLAIM TYPES: {claim_types}

Respond with valid JSON only, no other text:
{{
  "tools": [
    {{
      "name": "Tool Name",
      "url": "https://...",
      "description": "Brief description if mentioned",
      "category": "one of the categories above"
    }}
  ],
  "claims": [
    {{
      "tool_name": "Tool Name",
      "claim_type": "feature|pricing|integration|limitation|comparison|use_case",
      "content": "The specific claim text",
      "confidence": 0.7
    }}
  ]
}}

If no tools are mentioned, return: {{"tools": [], "claims": []}}
'''


class ClaudeAnalyzer(Analyzer):
    """Analyzer using Claude API for extraction."""

    def __init__(self, db: Database, config: dict = None):
        super().__init__(db, config)

        if not HAS_ANTHROPIC:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic"
            )

        api_key = self.config.get('api_key')
        if not api_key:
            raise ValueError("Anthropic API key required in config")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = self.config.get('model', 'claude-sonnet-4-20250514')
        self.max_tokens = self.config.get('max_tokens', 2000)

    def analyze(self, discovery: dict) -> AnalysisResult:
        """Analyze a discovery using Claude."""
        discovery_id = discovery['id']

        # Build the prompt
        metadata = discovery.get('metadata')
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        metadata = metadata or {}

        prompt = EXTRACTION_PROMPT.format(
            content=discovery.get('raw_text', '')[:4000],
            source_name=discovery.get('source_name', 'unknown'),
            source_url=discovery.get('source_url', ''),
            score=metadata.get('score', 'N/A'),
            categories=', '.join(TOOL_CATEGORIES),
            claim_types=', '.join(CLAIM_TYPES)
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text
            return self._parse_response(discovery_id, response_text)

        except Exception as e:
            return AnalysisResult(
                discovery_id=discovery_id,
                error=str(e)
            )

    def _parse_response(self, discovery_id: int, response_text: str) -> AnalysisResult:
        """Parse Claude's JSON response."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                return AnalysisResult(
                    discovery_id=discovery_id,
                    raw_response=response_text,
                    error="No JSON found in response"
                )

            data = json.loads(json_match.group())

            tools = []
            for t in data.get('tools', []):
                tools.append(ExtractedTool(
                    name=t.get('name', ''),
                    url=t.get('url'),
                    description=t.get('description'),
                    category=t.get('category', 'other')
                ))

            claims = []
            for c in data.get('claims', []):
                claims.append(ExtractedClaim(
                    tool_name=c.get('tool_name', ''),
                    claim_type=c.get('claim_type', 'feature'),
                    content=c.get('content', ''),
                    confidence=float(c.get('confidence', 0.5))
                ))

            return AnalysisResult(
                discovery_id=discovery_id,
                tools=tools,
                claims=claims,
                raw_response=response_text
            )

        except json.JSONDecodeError as e:
            return AnalysisResult(
                discovery_id=discovery_id,
                raw_response=response_text,
                error=f"JSON parse error: {e}"
            )


class MockAnalyzer(Analyzer):
    """Mock analyzer for testing without API calls."""

    def analyze(self, discovery: dict) -> AnalysisResult:
        """Extract tools using simple pattern matching."""
        discovery_id = discovery['id']
        raw_text = discovery.get('raw_text', '')

        # Simple pattern-based extraction for demo
        tools = []
        claims = []

        # Known tool patterns
        tool_patterns = [
            (r'Apollo\.?io|Apollo', 'Apollo', 'https://apollo.io', 'prospecting'),
            (r'Lavender\.?ai|Lavender', 'Lavender', 'https://lavender.ai', 'outreach'),
            (r'Instantly\.?ai|Instantly', 'Instantly', 'https://instantly.ai', 'outreach'),
            (r'Clay', 'Clay', 'https://clay.com', 'enrichment'),
            (r'Outreach\.?io|Outreach', 'Outreach', 'https://outreach.io', 'outreach'),
            (r'Gong\.?io|Gong', 'Gong', 'https://gong.io', 'conversation'),
            (r'ZoomInfo', 'ZoomInfo', 'https://zoominfo.com', 'enrichment'),
            (r'Lemlist', 'Lemlist', 'https://lemlist.com', 'outreach'),
            (r'Woodpecker', 'Woodpecker', 'https://woodpecker.co', 'outreach'),
            (r'Fireflies', 'Fireflies', 'https://fireflies.ai', 'conversation'),
            (r'HubSpot', 'HubSpot', 'https://hubspot.com', 'crm'),
            (r'Salesforce', 'Salesforce', 'https://salesforce.com', 'crm'),
            (r'Chorus', 'Chorus', 'https://chorus.ai', 'conversation'),
        ]

        seen_tools = set()
        for pattern, name, url, category in tool_patterns:
            if re.search(pattern, raw_text, re.IGNORECASE):
                if name.lower() not in seen_tools:
                    seen_tools.add(name.lower())
                    tools.append(ExtractedTool(
                        name=name,
                        url=url,
                        category=category
                    ))

                    # Extract surrounding context as a claim
                    match = re.search(
                        rf'.{{0,100}}{pattern}.{{0,100}}',
                        raw_text,
                        re.IGNORECASE
                    )
                    if match:
                        context = match.group().strip()
                        # Determine claim type from context
                        claim_type = 'feature'
                        if any(w in context.lower() for w in ['price', 'cost', '$', 'free', 'paid']):
                            claim_type = 'pricing'
                        elif any(w in context.lower() for w in ['integrat', 'connect', 'sync']):
                            claim_type = 'integration'
                        elif any(w in context.lower() for w in ['vs', 'compared', 'better than', 'alternative']):
                            claim_type = 'comparison'

                        claims.append(ExtractedClaim(
                            tool_name=name,
                            claim_type=claim_type,
                            content=context,
                            confidence=0.6
                        ))

        return AnalysisResult(
            discovery_id=discovery_id,
            tools=tools,
            claims=claims
        )


def run_analyzer(db: Database, config: dict = None, use_mock: bool = False) -> dict:
    """Run the analyzer on unprocessed discoveries."""
    config = config or {}

    if use_mock:
        analyzer = MockAnalyzer(db, config)
    else:
        analyzer = ClaudeAnalyzer(db, config)

    results = analyzer.process_discoveries(limit=config.get('limit', 10))

    # Summarize results
    total_tools = sum(len(r.tools) for r in results)
    total_claims = sum(len(r.claims) for r in results)
    errors = sum(1 for r in results if r.error)

    return {
        'processed': len(results),
        'tools_extracted': total_tools,
        'claims_extracted': total_claims,
        'errors': errors,
        'results': results
    }
