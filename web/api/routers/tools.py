"""
Tools Router

CRUD operations for tools.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from web.api.deps import get_current_user, get_db

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


class BulkStatusUpdate(BaseModel):
    """Bulk status update request."""
    tool_ids: list[int]
    status: str
    rejection_reason: Optional[str] = None


class ToolUpdate(BaseModel):
    """Tool update request."""
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    relevance_score: Optional[float] = None


@router.get("")
async def list_tools(
    status: Optional[str] = Query(None, description="Filter by status (comma-separated for multiple)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    min_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum relevance score"),
    max_score: Optional[float] = Query(None, ge=0, le=1, description="Maximum relevance score"),
    created_after: Optional[str] = Query(None, description="Filter tools created after date (ISO format)"),
    created_before: Optional[str] = Query(None, description="Filter tools created before date (ISO format)"),
    sort_by: str = Query("relevance_score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List tools with advanced filters and search."""
    db = get_db()
    conn = db.connect()

    # Build query
    query = "SELECT * FROM tools WHERE 1=1"
    params: list = []
    count_params: list = []

    # Status filter (supports multiple comma-separated values)
    if status:
        statuses = [s.strip() for s in status.split(",")]
        placeholders = ",".join("?" * len(statuses))
        query += f" AND status IN ({placeholders})"
        params.extend(statuses)
        count_params.extend(statuses)

    # Category filter
    if category:
        query += " AND category = ?"
        params.append(category)
        count_params.append(category)

    # Text search in name and description
    if search:
        search_term = f"%{search}%"
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([search_term, search_term])
        count_params.extend([search_term, search_term])

    # Score range filter
    if min_score is not None:
        query += " AND relevance_score >= ?"
        params.append(min_score)
        count_params.append(min_score)

    if max_score is not None:
        query += " AND relevance_score <= ?"
        params.append(max_score)
        count_params.append(max_score)

    # Date range filter
    if created_after:
        query += " AND created_at >= ?"
        params.append(created_after)
        count_params.append(created_after)

    if created_before:
        query += " AND created_at <= ?"
        params.append(created_before)
        count_params.append(created_before)

    # Get total count before pagination
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = conn.execute(count_query, count_params).fetchone()[0]

    # Sorting
    valid_sort_fields = ["relevance_score", "created_at", "name", "status", "category"]
    if sort_by not in valid_sort_fields:
        sort_by = "relevance_score"

    sort_direction = "ASC" if sort_order.lower() == "asc" else "DESC"

    # Handle NULL values in sorting
    if sort_by == "relevance_score":
        query += f" ORDER BY {sort_by} {sort_direction} NULLS LAST, created_at DESC"
    else:
        query += f" ORDER BY {sort_by} {sort_direction}"

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    tools = [dict(row) for row in rows]

    return {
        "tools": tools,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "status": status,
            "category": category,
            "search": search,
            "min_score": min_score,
            "max_score": max_score,
            "created_after": created_after,
            "created_before": created_before,
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
    }


@router.get("/{tool_id}")
async def get_tool(tool_id: int, current_user: dict = Depends(get_current_user)):
    """Get tool details with claims and related data."""
    db = get_db()
    conn = db.connect()
    tool = db.get_tool(tool_id)

    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    claims = db.get_claims_for_tool(tool_id)

    # Get changelog entries for this tool
    changelog = conn.execute(
        "SELECT * FROM changelog WHERE tool_id = ? ORDER BY detected_at DESC LIMIT 50",
        [tool_id]
    ).fetchall()

    # Get discoveries that mentioned this tool
    discoveries = conn.execute(
        """SELECT d.* FROM discoveries d
           JOIN claims c ON d.id = c.discovery_id
           WHERE c.tool_id = ?
           GROUP BY d.id
           ORDER BY d.discovered_at DESC LIMIT 20""",
        [tool_id]
    ).fetchall()

    return {
        **tool,
        "claims": claims,
        "changelog": [dict(row) for row in changelog],
        "discoveries": [dict(row) for row in discoveries],
    }


@router.put("/{tool_id}")
async def update_tool(
    tool_id: int,
    update: ToolUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update tool details."""
    db = get_db()
    conn = db.connect()

    tool = db.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Build update query dynamically
    updates: list[str] = []
    params: list[Any] = []

    if update.name is not None:
        updates.append("name = ?")
        params.append(update.name)

    if update.url is not None:
        updates.append("url = ?")
        params.append(update.url)

    if update.description is not None:
        updates.append("description = ?")
        params.append(update.description)

    if update.category is not None:
        updates.append("category = ?")
        params.append(update.category)

    if update.relevance_score is not None:
        updates.append("relevance_score = ?")
        params.append(update.relevance_score)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(tool_id)
    query = f"UPDATE tools SET {', '.join(updates)} WHERE id = ?"
    conn.execute(query, params)
    conn.commit()

    # Get updated tool
    updated_tool = db.get_tool(tool_id)

    return {
        "success": True,
        "tool": updated_tool,
    }


@router.delete("/{tool_id}")
async def delete_tool(tool_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a tool and its associated data."""
    db = get_db()
    conn = db.connect()

    tool = db.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Delete associated data
    conn.execute("DELETE FROM claims WHERE tool_id = ?", [tool_id])
    conn.execute("DELETE FROM changelog WHERE tool_id = ?", [tool_id])
    conn.execute("DELETE FROM tools WHERE id = ?", [tool_id])
    conn.commit()

    return {"success": True, "deleted_tool_id": tool_id}


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


@router.put("/bulk/status")
async def bulk_update_status(
    update: BulkStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Bulk update status for multiple tools."""
    db = get_db()

    valid_statuses = ["inbox", "analyzing", "review", "approved", "rejected"]
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    if not update.tool_ids:
        raise HTTPException(status_code=400, detail="No tool IDs provided")

    if len(update.tool_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tools per bulk operation")

    updated = []
    not_found = []

    for tool_id in update.tool_ids:
        tool = db.get_tool(tool_id)
        if not tool:
            not_found.append(tool_id)
            continue

        db.update_tool_status(tool_id, update.status, update.rejection_reason)
        updated.append(tool_id)

        # Log to changelog for approval
        if update.status == "approved":
            db.add_changelog_entry(
                tool_id,
                "new",
                f"Tool approved: {tool['name']}"
            )

    return {
        "success": True,
        "status": update.status,
        "updated": updated,
        "updated_count": len(updated),
        "not_found": not_found,
    }


@router.delete("/bulk")
async def bulk_delete_tools(
    tool_ids: list[int],
    current_user: dict = Depends(get_current_user)
):
    """Bulk delete tools."""
    db = get_db()
    conn = db.connect()

    if not tool_ids:
        raise HTTPException(status_code=400, detail="No tool IDs provided")

    if len(tool_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tools per bulk operation")

    deleted = []
    not_found = []

    for tool_id in tool_ids:
        tool = db.get_tool(tool_id)
        if not tool:
            not_found.append(tool_id)
            continue

        # Delete associated claims first
        conn.execute("DELETE FROM claims WHERE tool_id = ?", [tool_id])
        # Delete the tool
        conn.execute("DELETE FROM tools WHERE id = ?", [tool_id])
        deleted.append(tool_id)

    conn.commit()

    return {
        "success": True,
        "deleted": deleted,
        "deleted_count": len(deleted),
        "not_found": not_found,
    }
