# Glean Deployment Guide

This guide covers deploying Glean to production environments.

## Overview

Glean uses a multi-stage Docker build that:
1. Builds the React frontend with Node.js
2. Creates a slim Python production image
3. Serves both API and static frontend from a single container

## Quick Start

### Local Docker Testing

Test the production build locally before deploying:

```bash
# Build and run with docker-compose
make docker-compose-up

# Or manually:
make docker-build
make docker-run
```

Access the app at http://localhost:8080

### Deploy to Fly.io

**First-time setup:**

```bash
make deploy-first-time
```

This will:
- Launch a new Fly.io app
- Create a persistent volume for SQLite
- Generate and set a secure secret key
- Deploy the application

**Subsequent deployments:**

```bash
make deploy
```

## Fly.io Configuration

### fly.toml

The `fly.toml` file configures:

| Setting | Value | Description |
|---------|-------|-------------|
| `primary_region` | `iad` | US East (change as needed) |
| `internal_port` | `8080` | Container port |
| `auto_stop_machines` | `true` | Scale to zero when idle |
| `min_machines_running` | `0` | Allow full scale-down |

### Persistent Storage

SQLite database is stored on a persistent volume:

```toml
[[mounts]]
  source = "glean_data"
  destination = "/data"
  initial_size = "1gb"
```

The database path is configured via environment variable:
```
GLEAN_DB_PATH=/data/glean.db
```

### Secrets

Required secrets (set via `fly secrets set`):

| Secret | Description |
|--------|-------------|
| `GLEAN_SECRET_KEY` | JWT signing key (auto-generated on first deploy) |

Optional secrets (can also be configured in Settings UI):

| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | For Claude API access |
| `OPENAI_API_KEY` | For OpenAI API access |
| `REDDIT_CLIENT_ID` | Reddit OAuth client ID |
| `REDDIT_CLIENT_SECRET` | Reddit OAuth client secret |

Set secrets:
```bash
fly secrets set ANTHROPIC_API_KEY="sk-ant-..."
```

### Scaling

Adjust resources in `fly.toml`:

```toml
[[vm]]
  memory = "512mb"  # Increase for larger workloads
  cpu_kind = "shared"
  cpus = 1
```

For higher availability:
```toml
[http_service]
  min_machines_running = 1  # Keep at least one instance running
```

## Docker Configuration

### Dockerfile Stages

1. **frontend-builder**: Node 20 Alpine, builds React app
2. **production**: Python 3.11 slim, runs FastAPI with built frontend

### Build Arguments

None required. The build is self-contained.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Server port |
| `GLEAN_DB_PATH` | `db/glean.db` | SQLite database path |
| `GLEAN_SECRET_KEY` | (required) | JWT signing key |
| `CORS_ORIGINS` | `http://localhost:8080` | Allowed CORS origins |

## Database Migrations

Migrations run automatically on startup. The app checks for pending migrations and applies them before accepting requests.

To manually manage migrations:

```bash
# Check status
fly ssh console -C "python -m src.cli migrate status"

# Run migrations
fly ssh console -C "python -m src.cli migrate run"

# Rollback (careful!)
fly ssh console -C "python -m src.cli migrate rollback --yes"
```

## Monitoring

### Health Check

The app exposes a health endpoint:
```
GET /api/health
```

Response:
```json
{"status": "ok", "service": "glean-api", "production": true}
```

Fly.io automatically monitors this endpoint.

### Logs

View application logs:
```bash
make deploy-logs
# or
fly logs
```

### SSH Access

Connect to the running container:
```bash
make deploy-ssh
# or
fly ssh console
```

## Troubleshooting

### Build Failures

**Frontend build fails:**
- Check Node.js version compatibility (requires Node 20+)
- Verify `package-lock.json` is committed
- Run `npm ci` locally to test

**Python dependencies fail:**
- Ensure `pyproject.toml` has correct dependencies
- Check for platform-specific packages

### Runtime Issues

**Database errors:**
- Verify volume is mounted: `fly volumes list`
- Check permissions: `fly ssh console -C "ls -la /data"`
- Ensure migrations completed: check startup logs

**Authentication issues:**
- Verify `GLEAN_SECRET_KEY` is set: `fly secrets list`
- Check CORS configuration if frontend can't reach API

**502 Bad Gateway:**
- Check if app started: `fly status`
- Review logs for startup errors: `fly logs`
- Verify health check passes

### Recovery

**Recreate database volume:**
```bash
# Warning: This deletes all data!
fly volumes destroy glean_data
fly volumes create glean_data --region iad --size 1
fly deploy
```

**Force redeploy:**
```bash
fly deploy --force
```

## Alternative Deployments

### Docker Compose (Self-hosted)

Use the provided `docker-compose.yml`:

```bash
# Set environment variables
export GLEAN_SECRET_KEY=$(openssl rand -hex 32)

# Start services
docker compose up -d

# View logs
docker compose logs -f
```

### Manual Docker Run

```bash
docker build -t glean:latest .

docker run -d \
  --name glean \
  -p 8080:8080 \
  -e GLEAN_SECRET_KEY="your-secret-key" \
  -v glean_data:/data \
  glean:latest
```

## Security Considerations

1. **Secret Key**: Always use a strong, random secret key in production
2. **HTTPS**: Fly.io provides automatic HTTPS; ensure `force_https = true`
3. **Volume Backups**: Consider regular backups of the SQLite database
4. **Rate Limiting**: Not currently implemented; consider adding for public deployments

## Cost Estimation (Fly.io)

With default configuration (scale to zero):
- **Compute**: ~$0 when idle, ~$0.0000025/s when active
- **Storage**: ~$0.15/GB/month for persistent volume
- **Bandwidth**: Free tier includes generous allowance

Estimated monthly cost for light usage: **< $5**
