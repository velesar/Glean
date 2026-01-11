# Glean

Intelligence gathering system for discovering, analyzing, and curating AI tools for sales automation.

Glean continuously scans Reddit, Twitter/X, Product Hunt, web search, and RSS feeds to find new and existing AI tools relevant to sales automation. It processes raw discoveries through a multi-stage pipeline, extracting structured claims, scoring relevance, and presenting curated findings for human review.

## Features

- **Multi-Source Discovery**: Scouts for Reddit, Twitter/X, Product Hunt, web search, and RSS feeds
- **AI-Powered Analysis**: Uses Claude API to extract tools and claims from discoveries
- **Intelligent Curation**: Scores, ranks, and deduplicates tools automatically
- **Human-in-the-Loop Review**: Web UI for approving/rejecting curated tools
- **Update Tracking**: Monitors approved tools for pricing and feature changes
- **Report Generation**: Weekly digests and changelogs

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+
- SQLite (included with Python)

### Installation

```bash
# Clone the repository
git clone https://github.com/velesar/Glean.git
cd Glean

# Install dependencies
make install-dev

# Initialize database
make db-init

# Start development servers
make dev
```

This starts:
- Backend API at http://localhost:8000
- Frontend at http://localhost:5173

### First Run

1. Open http://localhost:5173 in your browser
2. Register a new account (first user becomes admin)
3. Go to **Jobs** page and run scouts in demo mode
4. Go to **Review** page to approve/reject discovered tools

## Project Structure

```
glean/
  src/
    cli.py              # CLI interface
    database.py         # SQLite database
    config.py           # Configuration
    migrations.py       # Database migrations
    analyzers/          # Claude-powered analysis
    curator/            # Scoring and ranking
    reporters/          # Report generation
    scouts/             # Data collectors
      reddit.py         # Reddit scout
      twitter.py        # Twitter/X scout
      producthunt.py    # Product Hunt scout
      websearch.py      # Web search scout
      rss.py            # RSS feed scout
    tracker/            # Update tracking
  web/
    api/                # FastAPI backend
    frontend/           # React + TypeScript frontend
  db/
    migrations/         # Database migration files
  docs/
    DEPLOYMENT.md       # Deployment guide
    DEVELOPMENT.md      # Development guide
    OPERATIONS.md       # Operations runbook
```

## CLI Commands

```bash
# Show help
glean --help

# Initialize database
glean init

# Show pipeline status
glean status

# Run scouts
glean scout reddit --demo      # Reddit (demo mode)
glean scout twitter --demo     # Twitter/X
glean scout producthunt --demo # Product Hunt
glean scout web --demo         # Web search
glean scout rss --demo         # RSS feeds
glean scout all --demo         # All scouts

# Process discoveries
glean analyze --mock           # Extract tools (mock mode)
glean curate                   # Score and rank

# Human review
glean review                   # Interactive CLI review

# Check for updates
glean update                   # Check approved tools

# Generate reports
glean report weekly            # Weekly digest
glean report changelog         # Recent changes
glean report index             # Tool index

# Database migrations
glean migrate status           # Show migration status
glean migrate run              # Apply migrations
glean migrate rollback         # Rollback last migration
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and configure:

```yaml
api_keys:
  anthropic:
    api_key: "sk-ant-..."      # For AI analysis

  reddit:
    client_id: "..."           # Reddit OAuth
    client_secret: "..."

  twitter:
    bearer_token: "..."        # Twitter API v2

  producthunt:
    api_key: "..."             # Product Hunt OAuth
    api_secret: "..."

  serpapi:
    api_key: "..."             # For web search

database:
  path: "db/glean.db"
```

API keys can also be configured in the web UI under Settings.

## Development

```bash
# Start development environment
make dev                       # Tmux with backend + frontend

# Or run separately
make backend                   # FastAPI backend only
make frontend                  # React frontend only

# Code quality
make lint                      # Run linters
make format                    # Format code
make test                      # Run tests

# Database
make db-migrate                # Apply migrations
make db-migrate-status         # Check migration status
make db-reset                  # Reset database (WARNING: deletes data)
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development guide.

## Deployment

### Docker

```bash
# Build and run locally
make docker-compose-up

# Or manually
make docker-build
make docker-run
```

### Fly.io

```bash
# First-time deployment
make deploy-first-time

# Subsequent deployments
make deploy
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment guide.

## Architecture

```
Sources -> Scouts -> Inbox -> Analyzers -> Review Queue -> HITL -> Approved
                                                              |
                                                          Rejected

Approved tools -> Update Tracker -> News/Releases -> Changelog -> Reports
```

### Pipeline Stages

1. **Inbox**: Raw scout findings
2. **Analyzing**: Claims being extracted
3. **Review**: Scored, ready for human review
4. **Approved**: Human-verified, in published index
5. **Rejected**: With rejection reasons

## API Documentation

When running, API docs are available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- [GitHub Issues](https://github.com/velesar/Glean/issues) - Bug reports and feature requests
- [Documentation](docs/) - Guides and runbooks
