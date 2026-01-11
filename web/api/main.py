"""
Glean Web API

FastAPI backend for the Glean web interface.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from web.api.deps import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    init_db()
    yield
    close_db()


app = FastAPI(
    title="Glean API",
    description="API for the Glean intelligence gathering system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers after app is created
from web.api.routers import auth, tools, jobs, reports, stats, settings

# Auth routes (public)
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# Protected routes
app.include_router(stats.router, prefix="/api", tags=["stats"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "glean-api"}
