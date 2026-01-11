.PHONY: help install install-dev setup dev backend frontend cli clean lint format test build db-init db-reset db-migrate db-migrate-status db-migrate-rollback db-migrate-create

# Default target
help:
	@echo "Glean - AI Sales Tools Intelligence Gathering System"
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install production dependencies"
	@echo "  make install-dev  Install development dependencies"
	@echo "  make setup        Full project setup (Python + Node)"
	@echo ""
	@echo "Development:"
	@echo "  make dev          Start all services in tmux"
	@echo "  make backend      Start FastAPI backend only"
	@echo "  make frontend     Start React frontend only"
	@echo "  make cli          Run CLI (use: make cli CMD='status')"
	@echo ""
	@echo "Database:"
	@echo "  make db-init      Initialize database schema"
	@echo "  make db-reset     Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "Migrations:"
	@echo "  make db-migrate          Apply pending migrations"
	@echo "  make db-migrate-status   Show migration status"
	@echo "  make db-migrate-rollback Rollback last migration"
	@echo "  make db-migrate-create   Create new migration (NAME=name)"
	@echo ""
	@echo "Quality:"
	@echo "  make lint         Run linters"
	@echo "  make format       Format code"
	@echo "  make test         Run tests"
	@echo ""
	@echo "Build:"
	@echo "  make build        Build frontend for production"
	@echo "  make clean        Clean build artifacts"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	cd web/frontend && npm install

setup: install-dev db-init
	@echo "Setup complete!"

# Development servers
dev:
	@chmod +x scripts/dev.sh
	@./scripts/dev.sh

backend:
	cd web/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd web/frontend && npm run dev

# CLI shortcut
cli:
	python -m src.cli $(CMD)

# Database
db-init:
	python -m src.cli init

db-reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	rm -f db/glean.db
	python -m src.cli migrate run

# Migrations
db-migrate:
	python -m src.cli migrate run

db-migrate-status:
	python -m src.cli migrate status

db-migrate-rollback:
	python -m src.cli migrate rollback --yes

db-migrate-create:
	@if [ -z "$(NAME)" ]; then echo "Usage: make db-migrate-create NAME=migration_name"; exit 1; fi
	python -m src.cli migrate create "$(NAME)"

# Code quality
lint:
	@echo "Linting Python..."
	-ruff check src/ web/
	@echo "Linting TypeScript..."
	cd web/frontend && npm run lint

format:
	@echo "Formatting Python..."
	-ruff format src/ web/
	@echo "Formatting TypeScript..."
	-cd web/frontend && npx prettier --write "src/**/*.{ts,tsx}"

test:
	pytest tests/ -v

# Build
build:
	cd web/frontend && npm run build

clean:
	rm -rf web/frontend/dist
	rm -rf web/frontend/node_modules/.vite
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Scout commands (shortcuts)
scout-demo:
	python -m src.cli scout reddit --demo

scout-analyze:
	python -m src.cli analyze

scout-curate:
	python -m src.cli curate

# Reports
report-weekly:
	python -m src.cli report weekly

report-changelog:
	python -m src.cli report changelog
