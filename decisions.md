# Glean Decision Log

Append-only log of architectural and process decisions.

---

## How to Use This File

When making a significant decision:

1. Add a new entry at the top (below the instructions)
2. Include: date, context, decision, rationale, alternatives considered
3. Never edit or delete past entries (append-only)

---

## Decisions

### 2026-01-11: Project Documentation Structure

**Context**: Setting up initial project structure for AI-assisted development.

**Decision**: Use three core documentation files:
- `CLAUDE.md` - AI assistant guidance and project overview
- `plan.md` - Hierarchical task breakdown with status tracking
- `glossary.md` - Definitions and taxonomy
- `decisions.md` - This append-only decision log

**Rationale**:
- Separating concerns makes each file focused and maintainable
- AI assistants can quickly find relevant context
- Append-only decisions log preserves history and prevents revisionism
- Plan.md with checkboxes enables visual progress tracking

**Alternatives Considered**:
- Single README.md with everything (rejected: too large, mixed concerns)
- Wiki-style folder (rejected: overhead for small project)

---

### 2026-01-11: SQLite as Primary Database

**Context**: Need to store tools, claims, sources, and pipeline state.

**Decision**: Use SQLite as the primary database.

**Rationale**:
- Zero configuration, file-based storage
- Sufficient for expected volume (hundreds to low thousands of tools)
- Easy backup (single file)
- Good Python support
- Can migrate to PostgreSQL later if needed

**Alternatives Considered**:
- PostgreSQL (rejected: overkill for initial scale, deployment complexity)
- JSON files (rejected: no query capability, concurrency issues)
- TinyDB (rejected: less mature, limited query language)

---

### 2026-01-11: Python as Implementation Language

**Context**: Choosing primary language for Glean implementation.

**Decision**: Use Python for all components.

**Rationale**:
- Excellent libraries for web scraping (requests, BeautifulSoup, PRAW)
- Strong LLM API support (anthropic SDK)
- Good CLI frameworks (Click, Typer)
- Rapid prototyping for experimental pipeline
- Wide familiarity for potential contributors

**Alternatives Considered**:
- TypeScript/Node (rejected: less mature scraping ecosystem)
- Go (rejected: slower iteration speed for prototype phase)

---

### 2026-01-11: Pipeline Stage Model

**Context**: Defining how tools flow through the system.

**Decision**: Use explicit pipeline stages: inbox → analyzing → review → approved/rejected

**Rationale**:
- Clear state machine with defined transitions
- Easy to query "what's in each stage"
- Supports pause/resume at any stage
- Enables metrics per stage (throughput, time-in-stage)

**Alternatives Considered**:
- Event sourcing (rejected: complexity not justified yet)
- Simple boolean flags (rejected: doesn't scale to multiple stages)

---

*Add new decisions above this line*
