"""
Export Router

Export tools and claims to CSV/JSON formats.
"""

import csv
import io
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from web.api.deps import get_current_user, get_db

router = APIRouter()


def _get_tools_data(
    status: Optional[str] = None,
    category: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
) -> list[dict]:
    """Get tools data with optional filters."""
    db = get_db()
    conn = db.connect()

    query = "SELECT * FROM tools WHERE 1=1"
    params: list = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if category:
        query += " AND category = ?"
        params.append(category)

    if min_score is not None:
        query += " AND relevance_score >= ?"
        params.append(min_score)

    if max_score is not None:
        query += " AND relevance_score <= ?"
        params.append(max_score)

    query += " ORDER BY relevance_score DESC NULLS LAST, created_at DESC"

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _get_claims_data(tool_ids: Optional[list[int]] = None) -> list[dict]:
    """Get claims data, optionally filtered by tool IDs."""
    db = get_db()
    conn = db.connect()

    query = """
        SELECT
            c.id, c.tool_id, c.claim_type, c.content, c.confidence,
            c.source_url, c.created_at,
            t.name as tool_name, t.url as tool_url,
            s.name as source_name
        FROM claims c
        LEFT JOIN tools t ON c.tool_id = t.id
        LEFT JOIN sources s ON c.source_id = s.id
        WHERE 1=1
    """
    params: list = []

    if tool_ids:
        placeholders = ",".join("?" * len(tool_ids))
        query += f" AND c.tool_id IN ({placeholders})"
        params.extend(tool_ids)

    query += " ORDER BY c.created_at DESC"

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


@router.get("/tools/json")
async def export_tools_json(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum relevance score"),
    max_score: Optional[float] = Query(None, ge=0, le=1, description="Maximum relevance score"),
    include_claims: bool = Query(False, description="Include claims for each tool"),
    current_user: dict = Depends(get_current_user),
):
    """Export tools to JSON format."""
    tools = _get_tools_data(status, category, min_score, max_score)

    if include_claims:
        db = get_db()
        for tool in tools:
            tool["claims"] = db.get_claims_for_tool(tool["id"])

    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "total_count": len(tools),
        "filters": {
            "status": status,
            "category": category,
            "min_score": min_score,
            "max_score": max_score,
        },
        "tools": tools,
    }

    json_content = json.dumps(export_data, indent=2, default=str)

    return StreamingResponse(
        io.BytesIO(json_content.encode()),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=glean_tools_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        },
    )


@router.get("/tools/csv")
async def export_tools_csv(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum relevance score"),
    max_score: Optional[float] = Query(None, ge=0, le=1, description="Maximum relevance score"),
    current_user: dict = Depends(get_current_user),
):
    """Export tools to CSV format."""
    tools = _get_tools_data(status, category, min_score, max_score)

    # Define CSV columns
    columns = [
        "id", "name", "url", "description", "category", "status",
        "relevance_score", "rejection_reason", "created_at", "reviewed_at"
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(tools)

    csv_content = output.getvalue()

    return StreamingResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=glean_tools_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@router.get("/claims/json")
async def export_claims_json(
    tool_id: Optional[int] = Query(None, description="Filter by tool ID"),
    current_user: dict = Depends(get_current_user),
):
    """Export claims to JSON format."""
    tool_ids = [tool_id] if tool_id else None
    claims = _get_claims_data(tool_ids)

    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "total_count": len(claims),
        "filters": {
            "tool_id": tool_id,
        },
        "claims": claims,
    }

    json_content = json.dumps(export_data, indent=2, default=str)

    return StreamingResponse(
        io.BytesIO(json_content.encode()),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=glean_claims_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        },
    )


@router.get("/claims/csv")
async def export_claims_csv(
    tool_id: Optional[int] = Query(None, description="Filter by tool ID"),
    current_user: dict = Depends(get_current_user),
):
    """Export claims to CSV format."""
    tool_ids = [tool_id] if tool_id else None
    claims = _get_claims_data(tool_ids)

    columns = [
        "id", "tool_id", "tool_name", "claim_type", "content",
        "confidence", "source_name", "source_url", "created_at"
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(claims)

    csv_content = output.getvalue()

    return StreamingResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=glean_claims_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@router.get("/all/json")
async def export_all_json(
    current_user: dict = Depends(get_current_user),
):
    """Export all data (tools, claims, changelog) to JSON."""
    db = get_db()
    conn = db.connect()

    # Get all tools with claims
    tools = _get_tools_data()
    for tool in tools:
        tool["claims"] = db.get_claims_for_tool(tool["id"])

    # Get changelog
    changelog_rows = conn.execute(
        "SELECT * FROM changelog ORDER BY detected_at DESC"
    ).fetchall()
    changelog = [dict(row) for row in changelog_rows]

    # Get sources
    sources_rows = conn.execute("SELECT * FROM sources").fetchall()
    sources = [dict(row) for row in sources_rows]

    # Get discoveries
    discoveries_rows = conn.execute(
        "SELECT * FROM discoveries ORDER BY discovered_at DESC LIMIT 1000"
    ).fetchall()
    discoveries = [dict(row) for row in discoveries_rows]

    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "version": "1.0",
        "tools": {
            "count": len(tools),
            "data": tools,
        },
        "changelog": {
            "count": len(changelog),
            "data": changelog,
        },
        "sources": {
            "count": len(sources),
            "data": sources,
        },
        "discoveries": {
            "count": len(discoveries),
            "data": discoveries,
        },
    }

    json_content = json.dumps(export_data, indent=2, default=str)

    return StreamingResponse(
        io.BytesIO(json_content.encode()),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=glean_full_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        },
    )
