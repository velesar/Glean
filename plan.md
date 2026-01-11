# Glean Development Plan

Hierarchical task breakdown for building the Glean intelligence gathering system.

## Legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete
- `[!]` Blocked

---

## Phase 0: Foundation

Core infrastructure and project setup.

### 0.1 Project Setup
- [x] Initialize repository
- [x] Add LICENSE
- [x] Create CLAUDE.md
- [x] Create plan.md (this file)
- [x] Create glossary.md
- [x] Create decisions.md
- [x] Set up config.yaml structure (with .gitignore for secrets)

### 0.2 Database Schema
- [x] Design SQLite schema for tools table
- [x] Design sources table (with reliability tracking)
- [x] Design claims table (linked to tools and sources)
- [x] Design changelog/events table
- [x] Design discoveries table (raw scout findings)
- [x] Create db initialization script
- [ ] Add sample seed data for testing

### 0.3 CLI Framework
- [x] Set up Python project structure (pyproject.toml)
- [x] Choose CLI framework (Click + Rich)
- [x] Implement base CLI with subcommand routing
- [x] Add `glean status` command (pipeline statistics)
- [ ] Add logging infrastructure

---

## Phase 1: Scout System

Data collection from external sources.

### 1.1 Scout Base
- [x] Define Scout abstract base class
- [x] Implement deduplication check (against inbox + later stages)
- [x] Implement rate limiting utilities
- [x] Keyword filtering for relevance detection
- [ ] Create source reliability tracking

### 1.2 Reddit Scout
- [x] Set up Reddit API access (OAuth + demo mode)
- [x] Define target subreddits (r/sales, r/SaaS, r/salesforce, etc.)
- [x] Implement post/comment extraction
- [x] Parse and normalize tool mentions
- [x] Store raw findings to discoveries table

### 1.3 Web Search Scout
- [ ] Evaluate search APIs (SerpAPI, Brave, etc.)
- [ ] Define search query templates for AI sales tools
- [ ] Implement result parsing
- [ ] Extract tool candidates from search results

### 1.4 Product Hunt Scout
- [ ] Set up Product Hunt API access
- [ ] Filter for sales/automation categories
- [ ] Extract launch data and metadata

### 1.5 Additional Scouts (v2)
- [ ] Twitter/X scout
- [ ] RSS/blog aggregator
- [ ] HackerNews scout
- [ ] GitHub trending scout

---

## Phase 2: Analysis Pipeline

Extract structured data and verify claims.

### 2.1 Analyzer Framework
- [x] Define Analyzer base class
- [x] Implement claim extraction prompt templates
- [x] Set up LLM integration (Claude API)
- [x] Create confidence scoring system
- [x] Mock analyzer for testing without API

### 2.2 Claim Extractor
- [x] Extract discrete claims from raw text
- [x] Categorize claims (features, pricing, integrations, etc.)
- [x] Assign initial confidence based on source reliability
- [ ] Handle multi-source claim aggregation

### 2.3 Tool Enrichment
- [ ] Fetch tool homepage and extract metadata
- [ ] Identify pricing information
- [ ] Extract feature lists
- [ ] Capture screenshots (optional)

### 2.4 Conflict Detection
- [ ] Detect contradictory claims across sources
- [ ] Flag for human review
- [ ] Track claim provenance

---

## Phase 3: Curation System

AI-driven ranking and queue management.

### 3.1 Relevance Scoring
- [x] Define relevance criteria for sales automation
- [x] Implement scoring model (keyword + category based)
- [x] Weight by claim count and confidence
- [x] Rank tools in review queue by score

### 3.2 Deduplication
- [x] Detect duplicate tool entries (fuzzy matching)
- [x] Merge claims from duplicate sources
- [x] Maintain canonical tool record

### 3.3 Review Queue
- [x] Prioritize queue by relevance score
- [x] Configurable min score threshold
- [ ] Track time-in-queue

---

## Phase 4: Human-in-the-Loop Review

Human approval and rejection workflow.

### 4.1 Review Interface
- [x] **Decision**: CLI interface for v1 (simple, fast)
- [x] Display tool summary with claims and sources
- [x] Show relevance scores with color coding
- [x] Enable approve/reject with optional reasons
- [x] Skip and quit options with session summary

### 4.2 Feedback Loop
- [x] Log rejection reasons to database
- [x] Log approvals to changelog
- [ ] Use rejections to improve curation scoring
- [ ] Track reviewer agreement metrics

---

## Phase 5: Update Tracking

Monitor approved tools for changes.

### 5.1 Change Detection
- [x] Webpage fetching for approved tools
- [x] Content hashing for change detection
- [x] Detect pricing changes (pattern matching)
- [x] Detect feature changes
- [x] Detect title/content updates
- [ ] Scheduled periodic checks (cron)

### 5.2 Changelog System
- [x] Record all changes with timestamps
- [x] Link changes to source URLs
- [x] Store page snapshots for comparison
- [ ] Generate diff summaries

---

## Phase 6: Reporting

Generate digests and summaries.

### 6.1 Report Framework
- [x] Define Markdown report templates
- [x] Save reports to reports/ directory
- [x] Group by date and category

### 6.2 Weekly Digest
- [x] Summarize new approved tools
- [x] Show updates detected
- [x] Include claims for each tool
- [x] Configurable time range (--weeks)

### 6.3 Changelog Report
- [x] List recent changes to all tracked tools
- [x] Filter by date range (--days)
- [x] Export to Markdown (--save)
- [x] Emoji icons for change types

### 6.4 Tools Index
- [x] Generate index of approved tools
- [x] Group by category
- [x] Include URLs and descriptions

---

## Phase 7: Publishing (v2)

Distribute curated findings.

- [ ] **Decision**: Choose publishing destination
- [ ] Export to static site / API / newsletter
- [ ] Implement publishing workflow
- [ ] Add scheduling (batch vs continuous)

---

## Dependencies

```
Phase 0 (Foundation)
    └── Phase 1 (Scouts)
            └── Phase 2 (Analyzers)
                    └── Phase 3 (Curation)
                            └── Phase 4 (HITL)
                                    ├── Phase 5 (Updates)
                                    └── Phase 6 (Reports)
                                            └── Phase 7 (Publishing)
```

---

## Immediate Next Steps

1. ~~Complete Phase 0 foundation files~~ ✓
2. ~~Design and implement database schema~~ ✓
3. ~~Set up Python project with CLI framework~~ ✓
4. Build first scout (Reddit recommended - good signal, accessible API)
5. Implement basic analyzer with Claude API integration

---

## Open Questions

- Which LLM to use for analysis? (Claude API recommended)
- What's the target volume? (tools/day, sources/day)
- How much human review capacity is available?
- What's the publishing destination?

---

*Last updated: 2026-01-11*
