# Glean Development Guide

This guide covers setting up a development environment and contributing to Glean.

## Prerequisites

- **Python 3.10+** with pip
- **Node.js 20+** with npm
- **Git**
- **tmux** (optional, for `make dev`)

## Initial Setup

### 1. Clone and Install

```bash
git clone https://github.com/velesar/Glean.git
cd Glean

# Install Python and Node dependencies
make install-dev
```

This installs:
- Python package in editable mode with dev dependencies
- Frontend npm packages

### 2. Initialize Database

```bash
make db-init
```

This creates `db/glean.db` with the schema and default sources.

### 3. Configure API Keys (Optional)

Copy and edit the configuration:

```bash
cp config.example.yaml config.yaml
```

API keys are optional - all scouts and analyzers support demo/mock modes for development.

## Development Workflow

### Starting the Dev Environment

**Option 1: Tmux (Recommended)**

```bash
make dev
```

This opens a tmux session with:
- Pane 0: Backend (FastAPI with hot reload)
- Pane 1: Frontend (Vite with HMR)
- Pane 2: Shell for running commands

Switch panes with `Ctrl+B` then arrow keys. Exit with `Ctrl+B` then `d`.

**Option 2: Separate Terminals**

```bash
# Terminal 1: Backend
make backend

# Terminal 2: Frontend
make frontend
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | React app |
| Backend API | http://localhost:8000 | FastAPI |
| API Docs | http://localhost:8000/docs | Swagger UI |

### First-Time Setup in UI

1. Navigate to http://localhost:5173
2. Register a new account (first user is automatically admin)
3. Explore the Dashboard, Jobs, Review, and Settings pages

## Project Architecture

### Backend (`web/api/`)

FastAPI application with:

```
web/api/
  main.py           # App entry point, lifespan, static serving
  deps.py           # Dependency injection (DB, auth)
  auth.py           # JWT token utilities
  routers/
    auth.py         # Login, register, user management
    jobs.py         # Background job management
    tools.py        # Tool CRUD and status updates
    reports.py      # Report generation endpoints
    settings.py     # User settings management
    stats.py        # Pipeline statistics
```

**Key patterns:**
- All routes require authentication via `Depends(get_current_user)`
- Background tasks use FastAPI's `BackgroundTasks`
- Database is SQLite, accessed via `src/database.py`

### Frontend (`web/frontend/`)

React + TypeScript + Vite application:

```
web/frontend/src/
  api.ts            # API client functions
  types.ts          # TypeScript type definitions
  App.tsx           # Router setup
  main.tsx          # Entry point
  hooks/
    useApi.ts       # React Query hooks
  contexts/
    AuthContext.tsx # Authentication state
  components/
    Layout.tsx      # App shell with nav
    ProtectedRoute.tsx
  pages/
    Dashboard.tsx   # Pipeline stats
    Jobs.tsx        # Run scouts/analyzers
    Review.tsx      # HITL tool review
    Tools.tsx       # Browse all tools
    Settings.tsx    # API key configuration
    Login.tsx       # Auth forms
```

**Key patterns:**
- React Query for data fetching (`@tanstack/react-query`)
- Tailwind CSS for styling
- JWT tokens stored in localStorage

### Core Library (`src/`)

```
src/
  cli.py            # Click CLI commands
  database.py       # SQLite wrapper
  config.py         # YAML config loading
  migrations.py     # Migration runner
  scouts/           # Data collectors
    base.py         # Abstract Scout class
    reddit.py       # Reddit API + demo data
    twitter.py      # Twitter API v2 + demo
    producthunt.py  # Product Hunt API + demo
    websearch.py    # SerpAPI/Google + demo
    rss.py          # RSS feed parser + demo
  analyzers/        # Tool extraction
    base.py         # Analyzer interface
    claude.py       # Claude API analyzer
    mock.py         # Pattern-matching mock
  curator/          # Scoring and ranking
    scorer.py       # Relevance scoring
    deduplicator.py # Duplicate detection
  reporters/        # Report generation
  tracker/          # Update monitoring
```

## Database

### Schema

See `src/database.py` for full schema. Key tables:

| Table | Purpose |
|-------|---------|
| `sources` | Data sources (reddit, twitter, etc.) |
| `tools` | Discovered AI tools |
| `claims` | Extracted claims about tools |
| `discoveries` | Raw scout findings |
| `changelog` | Tool update history |
| `users` | Authentication |
| `settings` | User preferences and API keys |

### Migrations

Migrations live in `db/migrations/` and are Python files with `up()` and `down()` functions.

```bash
# Check status
make db-migrate-status

# Apply pending migrations
make db-migrate

# Rollback last migration
make db-migrate-rollback

# Create new migration
make db-migrate-create NAME=add_some_table
```

Migrations run automatically on app startup in production.

### Reset Database

```bash
make db-reset
```

**Warning:** This deletes all data.

## Testing

### Running Tests

```bash
make test
```

Tests use pytest and are in the `tests/` directory.

### Test Structure

```
tests/
  conftest.py       # Fixtures
  test_database.py  # Database tests
  test_scouts.py    # Scout tests
  test_analyzers.py # Analyzer tests
```

### Demo/Mock Modes

All components support testing without API keys:

```bash
# Scouts with demo data
glean scout reddit --demo
glean scout twitter --demo

# Analyzer with pattern matching
glean analyze --mock
```

## Code Quality

### Linting

```bash
make lint
```

Uses:
- **ruff** for Python
- **eslint** for TypeScript

### Formatting

```bash
make format
```

Uses:
- **ruff format** for Python
- **prettier** for TypeScript

### Type Checking

```bash
# Python (via ruff)
ruff check src/

# TypeScript
cd web/frontend && npx tsc --noEmit
```

## Adding a New Scout

1. Create `src/scouts/newscout.py`:

```python
from src.scouts.base import Scout, Discovery, is_relevant

class NewScout(Scout):
    source_name = 'newscout'

    def run(self) -> list[Discovery]:
        if self.config.get('demo'):
            return self._get_demo_discoveries()
        # Real implementation
        ...

    def _get_demo_discoveries(self) -> list[Discovery]:
        return [
            Discovery(
                source_name='newscout',
                source_url='https://example.com/demo',
                raw_text='Demo discovery...',
                metadata={'type': 'demo'}
            )
        ]
```

2. Add to `src/scouts/__init__.py`

3. Add source to `src/database.py` `_seed_sources()`

4. Add CLI command in `src/cli.py`

5. Add to backend `web/api/routers/jobs.py`:
   - Add to `ScoutType` enum
   - Add to `run_single_scout()`
   - Add to `get_scout_types()` endpoint

6. Frontend automatically picks up new scout type

## Adding a New API Endpoint

1. Create or update router in `web/api/routers/`

2. Add types to `web/frontend/src/types.ts`

3. Add API function to `web/frontend/src/api.ts`

4. Add React Query hook to `web/frontend/src/hooks/useApi.ts`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GLEAN_DB_PATH` | `db/glean.db` | SQLite database path |
| `GLEAN_SECRET_KEY` | (required in prod) | JWT signing key |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `ANTHROPIC_API_KEY` | - | Claude API key |

## Debugging

### Backend Logs

FastAPI logs to stdout. In development, use:

```bash
uvicorn web.api.main:app --reload --log-level debug
```

### Frontend Dev Tools

React Query Devtools are included in development builds. Open with the floating button in the bottom-left corner.

### Database Inspection

```bash
# Open SQLite CLI
sqlite3 db/glean.db

# Useful queries
.tables
SELECT * FROM tools WHERE status = 'review';
SELECT * FROM discoveries WHERE processed = 0;
```

## Common Issues

### "No module named 'src'"

Install the package in editable mode:
```bash
pip install -e .
```

### "CORS error"

Check that `CORS_ORIGINS` includes your frontend URL.

### "JWT signature invalid"

Clear localStorage and re-login:
```javascript
localStorage.removeItem('glean_token')
```

### "Migration failed"

Check migration status and retry:
```bash
make db-migrate-status
make db-migrate
```

## Git Workflow

1. Create feature branch from `main`
2. Make changes with clear commits
3. Run `make lint` and `make test`
4. Push and create PR
5. Get review and merge

### Commit Message Format

```
<type>: <short description>

<optional body with details>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Example:
```
feat: Add Twitter scout with demo mode

- Implement TwitterScout class with API v2 support
- Add demo data for testing without credentials
- Wire up to CLI and web UI
```
