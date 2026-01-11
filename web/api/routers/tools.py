"""
Tools Router

CRUD operations for tools.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from web.api.deps import get_db, get_current_user


router = APIRouter()


class Tool(BaseModel):
    """Tool response model."""
    id: int
    name: str
    url: Optional[str]
    description: Optional[str]
    category: Optional[str]
    status: str
    relevance_score: Optional[float]
    rejection_reason: Optional[str]
    created_at: str
    reviewed_at: Optional[str]


class Claim(BaseModel):
    """Claim response model."""
    id: int
    claim_type: Optional[str]
    content: str
    confidence: float
    source_name: str
    source_reliability: Optional[str]


class ToolDetail(Tool):
    """Tool with claims."""
    claims: list[Claim]


class StatusUpdate(BaseModel):
    """Status update request."""
    status: str
    rejection_reason: Optional[str] = None


@router.get("")
async def list_tools(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List tools with optional filters."""
    db = get_db()
    conn = db.connect()

    # Build query
    query = "SELECT * FROM tools WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY relevance_score DESC NULLS LAST, created_at DESC"
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()

    # Get total count
    count_query = "SELECT COUNT(*) FROM tools WHERE 1=1"
    count_params = []
    if status:
        count_query += " AND status = ?"
        count_params.append(status)
    if category:
        count_query += " AND category = ?"
        count_params.append(category)

    total = conn.execute(count_query, count_params).fetchone()[0]

    tools = [dict(row) for row in rows]

    return {
        "tools": tools,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{tool_id}")
async def get_tool(tool_id: int, current_user: dict = Depends(get_current_user)):
    """Get tool details with claims."""
    db = get_db()
    tool = db.get_tool(tool_id)

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    claims = db.get_claims_for_tool(tool_id)

    return {
        **tool,
        "claims": claims,
    }


@router.put("/{tool_id}/status")
async def update_tool_status(tool_id: int, update: StatusUpdate, current_user: dict = Depends(get_current_user)):
    """Update tool status (approve/reject)."""
    db = get_db()
    tool = db.get_tool(tool_id)

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    valid_statuses = ["inbox", "analyzing", "review", "approved", "rejected"]
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    db.update_tool_status(tool_id, update.status, update.rejection_reason)

    # Log to changelog for approval
    if update.status == "approved":
        db.add_changelog_entry(
            tool_id,
            "new",
            f"Tool approved: {tool['name']}"
        )

    return {"success": True, "tool_id": tool_id, "status": update.status}


@router.get("/{tool_id}/claims")
async def get_tool_claims(tool_id: int, current_user: dict = Depends(get_current_user)):
    """Get claims for a specific tool."""
    db = get_db()
    tool = db.get_tool(tool_id)

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    claims = db.get_claims_for_tool(tool_id)

    return {"claims": claims}
