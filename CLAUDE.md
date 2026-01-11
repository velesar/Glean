# CLAUDE.md - AI Assistant Guide for Glean

This document provides guidance for AI assistants working with the Glean repository.

## Project Overview

**Glean** is an intelligence gathering system for discovering, analyzing, and curating AI tools for sales automation.

- **Repository**: velesar/Glean
- **License**: MIT
- **Status**: Active development, core features implemented

Glean continuously scans Reddit, Twitter/X, Product Hunt, web search, and RSS feeds to find new and existing AI tools relevant to sales automation. It processes raw discoveries through a multi-stage pipeline, extracting structured claims, scoring relevance, and presenting curated findings for human review.

## Quick Start

```bash
# Install dependencies
make install-dev

# Initialize database
make db-init

# Start development environment
make dev
```

This starts:
- Backend API at http://localhost:8000
- Frontend at http://localhost:5173

## Architecture Overview

```
Sources -> Scouts -> Inbox -> Analyzers -> Review Queue -> HITL -> Approved
                                                              |
                                                          Rejected

Approved tools -> Update Tracker -> News/Releases -> Changelog -> Reports
```

### Core Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Scouts** | Data collectors (Reddit, Twitter, Product Hunt, Web Search, RSS) | `src/scouts/` |
| **Analyzers** | Claude-powered tool extraction and claim analysis | `src/analyzers/` |
| **Curator** | Scoring, ranking, deduplication | `src/curator/` |
| **HITL Review** | Web UI for human approval/rejection | `web/frontend/` |
| **Update Tracker** | Monitor approved tools for changes | `src/tracker/` |
| **Reporter** | Generate digests and changelogs | `src/reporters/` |

### Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+, FastAPI, SQLite |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| AI | Claude API (Anthropic) |
| Deployment | Docker, Fly.io |

## Directory Structure

```
glean/
  CLAUDE.md              # This file - AI assistant guide
  README.md              # Project readme
  Makefile               # Build and dev commands
  pyproject.toml         # Python package config
  config.example.yaml    # Configuration template
  Dockerfile             # Production container
  fly.toml               # Fly.io deployment config

  src/
    cli.py               # Click CLI interface
    database.py          # SQLite database wrapper
    config.py            # Configuration loading
    migrations.py        # Database migration runner
    scouts/              # Data collection modules
      base.py            # Abstract Scout class
      reddit.py          # Reddit API scout
      twitter.py         # Twitter/X API scout
      producthunt.py     # Product Hunt API scout
      websearch.py       # Web search scout (SerpAPI/Google)
      rss.py             # RSS feed scout
    analyzers/           # Tool extraction
      base.py            # Analyzer interface
      claude.py          # Claude API analyzer
      mock.py            # Pattern-matching mock
    curator/             # Scoring and ranking
      scorer.py          # Relevance scoring
      deduplicator.py    # Duplicate detection
    reporters/           # Report generation
    tracker/             # Update monitoring

  web/
    api/                 # FastAPI backend
      main.py            # App entry, lifespan, static serving
      deps.py            # Dependency injection
      auth.py            # JWT authentication
      routers/           # API route handlers
        auth.py          # Login, register, user management
        jobs.py          # Background job management
        tools.py         # Tool CRUD
        reports.py       # Report generation
        settings.py      # User settings
        stats.py         # Pipeline statistics
    frontend/            # React application
      src/
        api.ts           # API client functions
        types.ts         # TypeScript types
        App.tsx          # Router setup
        hooks/           # React Query hooks
        contexts/        # Auth context
        components/      # Reusable components
        pages/           # Page components

  db/
    glean.db             # SQLite database (gitignored)
    migrations/          # Database migrations

  docs/
    DEVELOPMENT.md       # Development guide
    DEPLOYMENT.md        # Deployment guide
    OPERATIONS.md        # Operations runbook

  tests/                 # Test suite
```

## Key Concepts

### Tool Record

A discovered AI tool with structured metadata:

- **Name, URL, description**: Basic identification
- **Category**: Classification (see database schema)
- **Claims**: Extracted statements with confidence scores
- **Status**: `inbox` | `analyzing` | `review` | `approved` | `rejected`
- **Relevance Score**: 0-1 score from curator

### Pipeline Stages

1. **Inbox**: Raw scout discoveries, unprocessed
2. **Analyzing**: Claims being extracted by analyzer
3. **Review**: Scored, ready for human review in web UI
4. **Approved**: Human-verified, in published index
5. **Rejected**: With rejection reasons

### Scout Pattern

All scouts follow the same pattern:

```python
from src.scouts.base import Scout, Discovery

class NewScout(Scout):
    source_name = 'newscout'

    def run(self) -> list[Discovery]:
        if self.demo_mode:
            return self._get_demo_discoveries()
        # Real API implementation
        ...
```

## CLI Commands

```bash
# Initialize
glean init                     # Initialize database

# Pipeline status
glean status                   # Show pipeline statistics

# Scouts (data collection)
glean scout reddit --demo      # Reddit scout (demo mode)
glean scout twitter --demo     # Twitter/X scout
glean scout producthunt --demo # Product Hunt scout
glean scout web --demo         # Web search scout
glean scout rss --demo         # RSS feed scout
glean scout all --demo         # Run all scouts

# Analysis
glean analyze --mock           # Extract tools (mock mode)
glean analyze                  # Extract tools (Claude API)

# Curation
glean curate                   # Score and rank tools

# Review
glean review                   # CLI review interface

# Updates
glean update                   # Check approved tools for changes

# Reports
glean report weekly            # Generate weekly digest
glean report changelog         # Generate changelog
glean report index             # Generate tool index

# Database migrations
glean migrate status           # Check migration status
glean migrate run              # Apply pending migrations
glean migrate rollback         # Rollback last migration
```

## Development Workflow

### Running Locally

```bash
# Tmux environment (recommended)
make dev

# Or separate terminals
make backend   # Terminal 1
make frontend  # Terminal 2
```

### Code Quality

```bash
make lint      # Run linters (ruff, eslint)
make format    # Format code (ruff, prettier)
make test      # Run tests
```

### Database Operations

```bash
make db-init              # Initialize database
make db-migrate           # Apply migrations
make db-migrate-status    # Check status
make db-reset             # Reset database (WARNING: deletes data)
```

## API Keys and Configuration

### Configuration Methods

1. **config.yaml** (local development):
   ```yaml
   api_keys:
     anthropic:
       api_key: "sk-ant-..."
     reddit:
       client_id: "..."
       client_secret: "..."
   ```

2. **Web UI Settings** (stored in database)

3. **Environment Variables** (production):
   - `ANTHROPIC_API_KEY`
   - `GLEAN_SECRET_KEY` (required in production)
   - `CORS_ORIGINS`

### Demo/Mock Modes

All scouts and analyzers support testing without API keys:

```bash
glean scout reddit --demo    # Uses sample data
glean analyze --mock         # Pattern-matching analysis
```

## Development Guidelines

### Working Conventions

1. **Read before writing**: Always read existing code before modifications
2. **Follow patterns**: Match existing scout/analyzer patterns
3. **Demo modes**: All new components should support demo/mock modes
4. **Type hints**: Use Python type hints and TypeScript types
5. **Minimal changes**: Only modify what's necessary

### When Adding a New Scout

1. Create `src/scouts/newscout.py` following base pattern
2. Add to `src/scouts/__init__.py`
3. Add source to `src/database.py` `_seed_sources()`
4. Add CLI command in `src/cli.py`
5. Add to `web/api/routers/jobs.py` (ScoutType enum, run_single_scout)
6. Frontend automatically picks up new scout types

### When Adding an API Endpoint

1. Create/update router in `web/api/routers/`
2. Add types to `web/frontend/src/types.ts`
3. Add API function to `web/frontend/src/api.ts`
4. Add React Query hook to `web/frontend/src/hooks/useApi.ts`

### Code Style

- **Python**: PEP 8, ruff for linting/formatting
- **TypeScript**: ESLint, Prettier
- **Commits**: `<type>: <description>` (feat, fix, docs, refactor, test, chore)

### Security Considerations

- Never commit API keys or credentials
- Validate all external data from scouts
- Use environment variables for secrets in production
- Be mindful of API rate limits

## Deployment

### Docker

```bash
make docker-build          # Build image
make docker-run            # Run container
make docker-compose-up     # Full stack with compose
```

### Fly.io

```bash
make deploy-first-time     # Initial deployment
make deploy                # Subsequent deployments
```

See `docs/DEPLOYMENT.md` for full deployment guide.

## Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview and quick start |
| `docs/DEVELOPMENT.md` | Detailed development guide |
| `docs/DEPLOYMENT.md` | Deployment instructions |
| `docs/OPERATIONS.md` | Operations runbook |
| `CLAUDE.md` | This file - AI assistant guide |

## Useful Commands for AI Assistants

```bash
# Explore codebase
find src -name "*.py" -type f  # List Python files
grep -r "class.*Scout" src/    # Find scout classes

# Check current state
glean status                   # Pipeline stats
make db-migrate-status         # Migration status
git log --oneline -10          # Recent commits

# Test changes
make lint                      # Check code quality
make test                      # Run tests
```

---

*Last updated: 2026-01-11*
*Update this file as the project evolves to keep it accurate and useful.*
