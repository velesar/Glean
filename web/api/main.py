"""
Glean Web API

FastAPI backend for the Glean web interface.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.api.deps import close_db, init_db

# Check if running in production (static files exist)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"
IS_PRODUCTION = FRONTEND_DIR.exists()


def run_migrations():
    """Run pending database migrations on startup."""
    try:
        from src.migrations import Migrator
        db_path = os.environ.get("GLEAN_DB_PATH", "db/glean.db")
        migrator = Migrator(db_path)
        pending = migrator.get_pending_migrations()
        if pending:
            print(f"Running {len(pending)} pending migration(s)...")
            applied = migrator.migrate()
            for name in applied:
                print(f"  Applied: {name}")
        migrator.close()
    except Exception as e:
        print(f"Warning: Migration check failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Run migrations before initializing DB
    run_migrations()
    init_db()
    yield
    close_db()


app = FastAPI(
    title="Glean API",
    description="API for the Glean intelligence gathering system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend (development)
cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers after app is created
from web.api.routers import auth, jobs, reports, settings, stats, tools  # noqa: E402

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
    return {"status": "ok", "service": "glean-api", "production": IS_PRODUCTION}


# Serve static frontend in production
if IS_PRODUCTION:
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the SPA for all non-API routes."""
        # Don't serve SPA for API routes
        if full_path.startswith("api/"):
            return {"error": "Not found"}, 404

        # Serve static files if they exist
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # Otherwise serve index.html for SPA routing
        return FileResponse(FRONTEND_DIR / "index.html")
