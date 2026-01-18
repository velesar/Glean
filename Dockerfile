# Multi-stage Dockerfile for Glean
# Stage 1: Build React frontend
# Stage 2: Production Python image with built frontend

# ============================================
# Stage 1: Build frontend
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY web/frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY web/frontend/ ./

# Set production environment variables for Vite build
ENV VITE_DEMO_MODE_DEFAULT=false

# Build production bundle
RUN npm run build

# ============================================
# Stage 2: Production image
# ============================================
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd --gid 1000 glean && \
    useradd --uid 1000 --gid glean --shell /bin/bash --create-home glean

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY web/api/ ./web/api/
COPY web/__init__.py ./web/
COPY db/migrations/ ./db/migrations/

# Install Python dependencies
RUN pip install -e ".[web]"

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/dist ./web/frontend/dist

# Create data directory for SQLite
RUN mkdir -p /app/db && chown -R glean:glean /app

# Switch to non-root user
USER glean

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Start command
CMD ["uvicorn", "web.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
