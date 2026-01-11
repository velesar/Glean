"""
Deduplication Module

Detects and merges duplicate tool entries.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from src.database import Database


@dataclass
class DuplicateGroup:
    """A group of duplicate tools."""
    canonical_id: int
    canonical_name: str
    duplicate_ids: list[int]
    duplicate_names: list[str]
    similarity_scores: list[float]


def normalize_name(name: str) -> str:
    """Normalize a tool name for comparison."""
    if not name:
        return ""
    # Lowercase, remove common suffixes, strip whitespace
    normalized = name.lower().strip()
    normalized = re.sub(r'\.(io|ai|com|co|app)$', '', normalized)
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    return normalized


def normalize_url(url: str) -> str:
    """Normalize a URL for comparison."""
    if not url:
        return ""
    # Remove protocol, www, trailing slash
    normalized = url.lower().strip()
    normalized = re.sub(r'^https?://', '', normalized)
    normalized = re.sub(r'^www\.', '', normalized)
    normalized = normalized.rstrip('/')
    return normalized


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def find_duplicates(db: Database, threshold: float = 0.85) -> list[DuplicateGroup]:
    """Find groups of duplicate tools."""
    conn = db.connect()

    # Get all tools
    rows = conn.execute(
        "SELECT id, name, url FROM tools ORDER BY id"
    ).fetchall()

    tools = [dict(row) for row in rows]
    if len(tools) < 2:
        return []

    # Track which tools have been grouped
    grouped = set()
    groups = []

    for i, tool1 in enumerate(tools):
        if tool1['id'] in grouped:
            continue

        name1_norm = normalize_name(tool1['name'])
        url1_norm = normalize_url(tool1['url'])

        duplicates = []
        dup_names = []
        dup_scores = []

        for tool2 in tools[i + 1:]:
            if tool2['id'] in grouped:
                continue

            name2_norm = normalize_name(tool2['name'])
            url2_norm = normalize_url(tool2['url'])

            # Check for matches
            name_sim = similarity(name1_norm, name2_norm)
            url_sim = similarity(url1_norm, url2_norm) if url1_norm and url2_norm else 0

            # Match if names are very similar or URLs match
            if name_sim >= threshold or (url_sim >= 0.9 and url1_norm):
                duplicates.append(tool2['id'])
                dup_names.append(tool2['name'])
                dup_scores.append(max(name_sim, url_sim))
                grouped.add(tool2['id'])

        if duplicates:
            grouped.add(tool1['id'])
            groups.append(DuplicateGroup(
                canonical_id=tool1['id'],
                canonical_name=tool1['name'],
                duplicate_ids=duplicates,
                duplicate_names=dup_names,
                similarity_scores=dup_scores
            ))

    return groups


def merge_duplicates(db: Database, canonical_id: int, duplicate_ids: list[int]):
    """Merge duplicate tools into the canonical entry.

    - Moves all claims from duplicates to canonical
    - Deletes the duplicate tool entries
    """
    conn = db.connect()

    for dup_id in duplicate_ids:
        # Move claims to canonical tool
        conn.execute(
            "UPDATE claims SET tool_id = ? WHERE tool_id = ?",
            (canonical_id, dup_id)
        )

        # Update discoveries to point to canonical
        conn.execute(
            "UPDATE discoveries SET tool_id = ? WHERE tool_id = ?",
            (canonical_id, dup_id)
        )

        # Delete duplicate tool
        conn.execute("DELETE FROM tools WHERE id = ?", (dup_id,))

    conn.commit()


def run_deduplication(db: Database, auto_merge: bool = False, threshold: float = 0.85) -> dict:
    """Run deduplication and optionally merge."""
    groups = find_duplicates(db, threshold)

    merged = 0
    if auto_merge:
        for group in groups:
            merge_duplicates(db, group.canonical_id, group.duplicate_ids)
            merged += len(group.duplicate_ids)

    return {
        'groups_found': len(groups),
        'duplicates_found': sum(len(g.duplicate_ids) for g in groups),
        'merged': merged,
        'groups': groups
    }
