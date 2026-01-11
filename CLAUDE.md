# CLAUDE.md - AI Assistant Guide for Glean

This document provides guidance for AI assistants working with the Glean repository.

## Project Overview

**Glean** is an intelligence gathering system for discovering, analyzing, and curating AI tools for sales automation.

- **Repository**: velesar/Glean
- **License**: MIT
- **Status**: Project initialization phase

Glean continuously scans Reddit, social networks, web search, and other sources to find new and existing AI tools relevant to sales automation. It processes raw discoveries through a multi-stage pipeline, extracting structured claims, scoring relevance, and presenting curated findings for human review before publishing.

## Architecture Overview

```
Sources → Scouts → Inbox → Analyzers → Review Queue → HITL → Approved → Publishing
                                                          ↓
                                                      Rejected (with reasons)

Approved tools → Update Tracker → News/Releases → Changelog → Reports
```

### Core Components

| Component | Purpose |
|-----------|---------|
| **Scouts** | Data collectors for specific sources (Reddit, Twitter/X, Product Hunt, web search, RSS) |
| **Analyzers** | Extract structured data, verify claims, score relevance |
| **Curator** | AI-driven ranking, deduplication, review queue management |
| **HITL Review** | Human approval/rejection interface |
| **Update Tracker** | Monitor approved tools for news, releases, changes |
| **Reporter** | Generate "what's new" digests and changelogs |

## Directory Structure

```
glean/
  CLAUDE.md              # this file
  plan.md                # hierarchical task breakdown, status
  glossary.md            # definitions, taxonomy
  decisions.md           # append-only log of architectural/process choices
  config.yaml            # API keys, source configs, thresholds

  db/
    glean.db             # SQLite: tools, sources, pipeline state, changelog

  src/
    scouts/              # source-specific collection scripts
    analyzers/           # extraction and verification
    curator/             # AI ranking and queue management
    reporters/           # changelog and digest generation
    cli.py               # main CLI interface

  kb/                    # human-readable exports (markdown snapshots of db)
  reports/               # generated reports (weekly digests, etc.)
```

## Key Concepts

### Tool Record

A discovered AI tool with structured metadata:

- **Name, URL, description**: Basic identification
- **Category**: See glossary.md for taxonomy
- **Claims**: Extracted from sources, with confidence scores
- **Sources**: Where discovered, when, reliability rating
- **Status**: `inbox` | `analyzing` | `review` | `approved` | `rejected`
- **Changelog**: Version history, news, updates

### Pipeline Stages

1. **Inbox**: Raw scout findings, unprocessed
2. **Analyzing**: Claims being extracted and verified
3. **Review Queue**: AI-curated, scored, ready for human review
4. **Approved**: Human-verified, included in published index
5. **Rejected**: With rejection reasons (used to improve future curation)

### Source Reliability

Sources are rated over time based on:

- Signal-to-noise ratio (useful discoveries vs spam)
- Claim accuracy (how often claims verify)
- Freshness (how quickly new tools appear there)

## CLI Commands (planned)

```bash
glean scout reddit          # run reddit scout
glean scout all             # run all scouts
glean analyze               # process inbox through analyzers
glean curate                # AI ranking and queue preparation
glean review                # HITL review interface
glean report weekly         # generate weekly digest
glean report changelog      # generate recent changes report
glean status                # pipeline statistics
```

## Development Guidelines

### Working Conventions

#### When Adding New Features

1. Check `plan.md` for current priorities and dependencies
2. Review `decisions.md` for relevant past choices
3. Update `glossary.md` if introducing new terminology
4. Log significant decisions in `decisions.md`

#### When Running Scouts

- Never duplicate sources already in inbox or later stages
- Always capture source URL, timestamp, raw text
- Tag with source reliability rating at time of capture

#### When Analyzing

- Extract claims as discrete, verifiable statements
- Assign confidence scores (0-1) based on source reliability and claim specificity
- Flag conflicting claims across sources for human review

#### When Generating Reports

- Diff against previous state to identify changes
- Group by: new tools, updated tools, news/releases
- Include source attribution for all claims

### Code Style

- Follow Python best practices (PEP 8)
- Use meaningful variable and function names
- Keep functions focused and single-purpose
- Avoid deep nesting; prefer early returns

### Git Workflow

1. **Branch naming**: Use descriptive branch names (e.g., `feature/reddit-scout`, `fix/claim-extraction`)
2. **Commit messages**: Write clear, concise commit messages describing the "why"
3. **Small commits**: Make atomic commits that represent logical units of work

### Security Considerations

- Never commit API keys or credentials to the repository
- Store secrets in `config.yaml` (gitignored) or environment variables
- Validate all external data from scouts
- Be cautious with web scraping rate limits and terms of service

## Open Decisions

Tracked in `decisions.md`. Key pending:

- HITL interface choice (CLI / web UI / external tool)
- Publishing destination
- Update frequency (batch vs continuous)
- Specific sources to include in v1

## Useful Context for AI Assistants

When working on this codebase:

- **Read before writing**: Always read existing code before making modifications
- **Check plan.md**: Understand current priorities before starting new work
- **Respect existing patterns**: Match the style and conventions already in use
- **Document decisions**: Log significant architectural choices in `decisions.md`
- **Minimal changes**: Only modify what's necessary for the task at hand
- **Test your work**: Verify scouts and analyzers work correctly before committing

---

*Last updated: 2026-01-11*
*Update this file as the project evolves to keep it accurate and useful.*
