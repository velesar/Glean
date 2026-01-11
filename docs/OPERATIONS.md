# Glean Operations Runbook

This runbook covers production operations, monitoring, troubleshooting, and maintenance for Glean.

## Table of Contents

1. [System Overview](#system-overview)
2. [Health Checks](#health-checks)
3. [Common Operations](#common-operations)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Backup and Recovery](#backup-and-recovery)
7. [Scaling](#scaling)
8. [Security](#security)

## System Overview

### Components

| Component | Port | Description |
|-----------|------|-------------|
| FastAPI Backend | 8000 | API server, background jobs |
| React Frontend | 5173 (dev) | Web UI (served by backend in prod) |
| SQLite Database | - | Data persistence |

### Key Directories

```
/app/                    # Application root (in container)
  db/glean.db           # SQLite database
  reports/              # Generated reports
  logs/                 # Application logs (if configured)
```

### Process Architecture

```
Main Process (uvicorn)
  ├── FastAPI Application
  │   ├── API Routes
  │   └── Background Tasks (scouts, analyzers, etc.)
  └── Static File Serving (frontend)
```

## Health Checks

### API Health

```bash
# Basic health check
curl -f http://localhost:8000/api/health

# With authentication (requires valid token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/stats
```

### Database Health

```bash
# Check database file exists and is readable
sqlite3 db/glean.db "SELECT COUNT(*) FROM tools;"

# Check migration status
glean migrate status
```

### Docker Health

```bash
# Check container status
docker ps | grep glean

# View container logs
docker logs glean-app --tail 100

# Check resource usage
docker stats glean-app
```

### Fly.io Health

```bash
# Check app status
fly status -a glean

# View recent logs
fly logs -a glean

# Check instances
fly scale show -a glean
```

## Common Operations

### Starting/Stopping

**Local Docker:**

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart
```

**Fly.io:**

```bash
# Deploy (restart with new code)
fly deploy -a glean

# Scale to 0 (stop)
fly scale count 0 -a glean

# Scale back up
fly scale count 1 -a glean
```

### Running Scouts

**Via Web UI:**
1. Navigate to Jobs page
2. Select scout type
3. Toggle demo mode off for real data
4. Click "Run"

**Via CLI:**

```bash
# In container
docker exec glean-app glean scout reddit
docker exec glean-app glean scout all --demo

# On Fly.io
fly ssh console -a glean -C "glean scout reddit"
```

### Processing Pipeline

```bash
# Run full pipeline
glean scout all          # Collect discoveries
glean analyze            # Extract tools and claims
glean curate             # Score and rank

# Check pipeline status
glean status
```

### Generating Reports

```bash
# Weekly digest
glean report weekly

# Changelog
glean report changelog

# Tool index
glean report index
```

### Database Operations

```bash
# Apply pending migrations
glean migrate run

# Check migration status
glean migrate status

# Rollback last migration (use with caution)
glean migrate rollback
```

## Monitoring

### Key Metrics to Watch

| Metric | Normal Range | Alert Threshold |
|--------|-------------|-----------------|
| API Response Time | < 200ms | > 1000ms |
| Error Rate | < 1% | > 5% |
| Database Size | < 1GB | > 5GB |
| Discovery Queue | < 1000 | > 5000 |
| Memory Usage | < 512MB | > 1GB |

### Log Locations

**Local:**
- Application logs: stdout/stderr (docker logs)
- Uvicorn access logs: stdout

**Fly.io:**
- All logs available via `fly logs`

### Important Log Patterns

```bash
# Find errors
docker logs glean-app 2>&1 | grep -i error

# Find failed jobs
docker logs glean-app 2>&1 | grep "FAILED"

# Find authentication issues
docker logs glean-app 2>&1 | grep -i "401\|unauthorized"
```

### Setting Up Alerts

For Fly.io, use the metrics endpoint:

```bash
# Export metrics (if configured)
curl http://localhost:8000/metrics
```

## Troubleshooting

### Common Issues

#### 1. "Database is locked"

**Symptoms:** API returns 500 errors, "database is locked" in logs

**Cause:** Multiple processes writing to SQLite simultaneously

**Solution:**
```bash
# Stop the application
docker-compose down

# Check for lingering processes
lsof db/glean.db

# Restart
docker-compose up -d
```

#### 2. "JWT signature invalid"

**Symptoms:** Users can't log in, 401 errors

**Cause:** GLEAN_SECRET_KEY changed or not set

**Solution:**
```bash
# Verify secret is set
echo $GLEAN_SECRET_KEY

# On Fly.io
fly secrets list -a glean

# Users need to re-login (clear localStorage)
```

#### 3. Scout Job Stuck at "Running"

**Symptoms:** Job shows 10% progress indefinitely

**Cause:** External API timeout or rate limit

**Solution:**
```bash
# Check logs for the specific job
docker logs glean-app 2>&1 | grep "scout"

# Cancel the job via API
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/jobs/$JOB_ID

# Retry with demo mode first
```

#### 4. "No module named 'src'"

**Symptoms:** CLI commands fail

**Cause:** Package not installed in editable mode

**Solution:**
```bash
pip install -e .
```

#### 5. CORS Errors

**Symptoms:** Frontend can't reach API

**Cause:** CORS_ORIGINS not configured correctly

**Solution:**
```bash
# Set correct origin
export CORS_ORIGINS="https://your-domain.fly.dev"

# Or for local development
export CORS_ORIGINS="http://localhost:5173"
```

#### 6. Out of Memory

**Symptoms:** Container restarts, OOMKilled status

**Cause:** Large analysis jobs, memory leak

**Solution:**
```bash
# Increase memory limit
docker-compose up -d --scale app=1 --memory=1g

# On Fly.io
fly scale memory 1024 -a glean

# Reduce batch sizes in jobs
glean analyze --limit 5
```

### Diagnostic Commands

```bash
# Database statistics
sqlite3 db/glean.db "
  SELECT 'tools', COUNT(*) FROM tools
  UNION ALL
  SELECT 'discoveries', COUNT(*) FROM discoveries
  UNION ALL
  SELECT 'claims', COUNT(*) FROM claims;
"

# Pipeline status breakdown
sqlite3 db/glean.db "
  SELECT status, COUNT(*)
  FROM tools
  GROUP BY status;
"

# Recent activity
sqlite3 db/glean.db "
  SELECT name, status, last_updated
  FROM tools
  ORDER BY last_updated DESC
  LIMIT 10;
"

# Check for stale discoveries
sqlite3 db/glean.db "
  SELECT COUNT(*)
  FROM discoveries
  WHERE processed = 0
  AND discovered_at < datetime('now', '-7 days');
"
```

## Backup and Recovery

### Automated Backups

**Fly.io with Volume Snapshots:**

```bash
# List snapshots
fly volumes list -a glean
fly volumes snapshots list vol_xxxxx -a glean

# Create manual snapshot
fly volumes snapshots create vol_xxxxx -a glean
```

**Local/Docker:**

```bash
# Backup database
cp db/glean.db db/backups/glean-$(date +%Y%m%d-%H%M%S).db

# With gzip
sqlite3 db/glean.db ".dump" | gzip > db/backups/glean-$(date +%Y%m%d).sql.gz
```

### Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/app/db/backups"
DB_PATH="/app/db/glean.db"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Create backup
BACKUP_FILE="$BACKUP_DIR/glean-$(date +%Y%m%d-%H%M%S).db"
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
gzip "$BACKUP_FILE"

# Remove old backups
find "$BACKUP_DIR" -name "*.db.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

### Recovery Procedures

#### Restore from Backup

```bash
# Stop the application
docker-compose down

# Restore database
gunzip -c db/backups/glean-20240115.sql.gz | sqlite3 db/glean.db.new
mv db/glean.db db/glean.db.old
mv db/glean.db.new db/glean.db

# Run migrations (if needed)
glean migrate run

# Restart
docker-compose up -d
```

#### Restore from Fly.io Snapshot

```bash
# List available snapshots
fly volumes snapshots list vol_xxxxx -a glean

# Restore from snapshot (creates new volume)
fly volumes create data --snapshot-id snap_xxxxx -a glean

# Update fly.toml to use new volume, then deploy
fly deploy -a glean
```

### Disaster Recovery

1. **Full Data Loss:**
   - Restore from most recent backup
   - Re-run scouts to repopulate discoveries
   - Re-analyze and re-curate

2. **Corrupted Database:**
   ```bash
   # Check integrity
   sqlite3 db/glean.db "PRAGMA integrity_check;"

   # Attempt repair
   sqlite3 db/glean.db ".recover" | sqlite3 db/glean-recovered.db
   ```

3. **Lost Credentials:**
   - Generate new `GLEAN_SECRET_KEY`
   - All users will need to re-login
   - Admin can reset passwords via CLI if needed

## Scaling

### Vertical Scaling

**Fly.io:**

```bash
# Increase memory
fly scale memory 1024 -a glean

# Increase CPU
fly scale vm shared-cpu-2x -a glean
```

**Docker:**

```yaml
# docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2'
```

### Horizontal Scaling Considerations

Glean uses SQLite, which doesn't support multiple writers. For horizontal scaling:

1. **Read Replicas:** Use Litestream to replicate to S3, serve reads from replicas
2. **Database Migration:** Migrate to PostgreSQL for multi-instance deployments
3. **Job Queue:** Use Redis for job distribution across workers

### Performance Optimization

```bash
# Vacuum database (reclaim space)
sqlite3 db/glean.db "VACUUM;"

# Analyze tables (update statistics)
sqlite3 db/glean.db "ANALYZE;"

# Check index usage
sqlite3 db/glean.db "EXPLAIN QUERY PLAN SELECT * FROM tools WHERE status = 'review';"
```

## Security

### Secret Management

**Required Secrets:**
- `GLEAN_SECRET_KEY`: JWT signing key (required in production)

**Optional Secrets:**
- `ANTHROPIC_API_KEY`: For Claude analysis
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`: Reddit API
- `TWITTER_BEARER_TOKEN`: Twitter API
- `SERPAPI_KEY`: Web search

**Fly.io Secrets:**

```bash
# Set secrets
fly secrets set GLEAN_SECRET_KEY="$(openssl rand -hex 32)" -a glean

# List secrets (shows names only)
fly secrets list -a glean

# Unset a secret
fly secrets unset SOME_KEY -a glean
```

### Access Control

- First registered user becomes admin
- Only admins can access Settings page
- All API endpoints require authentication

### Security Checklist

- [ ] Strong `GLEAN_SECRET_KEY` set (at least 32 bytes)
- [ ] HTTPS enabled (automatic on Fly.io)
- [ ] CORS restricted to known origins
- [ ] Database file permissions restricted (600)
- [ ] Backups encrypted at rest
- [ ] API keys stored as secrets, not in code
- [ ] Regular security updates applied

### Audit Logging

```sql
-- View recent logins
SELECT username, last_login FROM users ORDER BY last_login DESC;

-- View tool review activity
SELECT t.name, t.status, t.reviewed_at, t.rejection_reason
FROM tools t
WHERE t.reviewed_at IS NOT NULL
ORDER BY t.reviewed_at DESC;
```

## Maintenance Windows

### Recommended Schedule

| Task | Frequency | Duration |
|------|-----------|----------|
| Database vacuum | Weekly | 5-10 min |
| Log rotation | Daily | Automatic |
| Backup verification | Weekly | 10 min |
| Security updates | Monthly | 30 min |
| Full system test | After deploys | 15 min |

### Pre-Maintenance Checklist

1. Notify users of planned downtime
2. Create fresh backup
3. Verify backup integrity
4. Note current version/commit
5. Have rollback plan ready

### Post-Maintenance Checklist

1. Verify all services running
2. Run health checks
3. Test critical user flows
4. Monitor logs for errors
5. Update status page/notify users

## Contact and Escalation

### Support Channels

- GitHub Issues: https://github.com/velesar/Glean/issues
- Documentation: `docs/` directory

### Escalation Path

1. **L1 - Self-Service:**
   - Check this runbook
   - Review application logs
   - Check Fly.io/Docker status

2. **L2 - Team:**
   - Complex troubleshooting
   - Database issues
   - Performance problems

3. **L3 - External:**
   - Fly.io support (infrastructure)
   - Anthropic support (Claude API)
   - Third-party API issues
