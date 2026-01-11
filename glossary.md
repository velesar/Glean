# Glean Glossary

Definitions and taxonomy for the Glean system.

---

## Core Concepts

### Tool
A software product (typically SaaS) that provides AI-powered functionality for sales automation. Each tool is tracked as a record in the database with metadata, claims, and status.

### Claim
A discrete, verifiable statement about a tool extracted from a source. Claims have confidence scores and are linked to their source for provenance.

### Source
An external location where tool information is discovered (Reddit post, Product Hunt page, blog article, etc.). Sources have reliability ratings that evolve over time.

### Scout
An automated data collector that monitors a specific source type (Reddit, web search, etc.) and captures raw findings into the inbox.

### Analyzer
A processing component that extracts structured claims from raw scout findings, assigns confidence scores, and enriches tool records.

### Curator
The AI-driven system that ranks, deduplicates, and prioritizes tools for human review.

### HITL (Human-in-the-Loop)
The human review process where a person approves or rejects tool entries before they're published.

---

## Pipeline Stages

| Stage | Description |
|-------|-------------|
| **Inbox** | Raw, unprocessed scout findings |
| **Analyzing** | Currently being processed by analyzers |
| **Review** | AI-curated and ready for human review |
| **Approved** | Human-verified, included in published index |
| **Rejected** | Declined with reasons (used to improve curation) |

---

## Tool Categories

Primary categories for sales automation tools:

### Prospecting & Lead Generation
- Lead databases
- Contact enrichment
- Intent data providers
- Lead scoring

### Outreach & Engagement
- Email automation
- Sequence builders
- Cold calling assistants
- LinkedIn automation

### Conversation Intelligence
- Call recording & transcription
- Meeting assistants
- Coaching & feedback
- Sentiment analysis

### CRM & Pipeline
- CRM platforms
- Pipeline management
- Forecasting
- Deal intelligence

### Content & Proposals
- Proposal generators
- Content personalization
- Video messaging
- Document tracking

### Analytics & Reporting
- Revenue intelligence
- Activity tracking
- Performance dashboards
- Attribution

### Workflow & Integration
- Sales automation platforms
- Integration tools
- Data sync
- Workflow builders

---

## Claim Types

| Type | Example |
|------|---------|
| **Feature** | "Includes AI-powered email writing" |
| **Pricing** | "Starts at $49/month" |
| **Integration** | "Integrates with Salesforce" |
| **Limitation** | "No API access on basic plan" |
| **Comparison** | "Alternative to Outreach.io" |
| **Use Case** | "Best for enterprise SDR teams" |

---

## Confidence Scores

Claims are scored 0.0 to 1.0 based on:

| Range | Meaning |
|-------|---------|
| 0.9 - 1.0 | Verified from official source |
| 0.7 - 0.9 | High confidence, reliable source |
| 0.5 - 0.7 | Moderate confidence, needs verification |
| 0.3 - 0.5 | Low confidence, single unverified source |
| 0.0 - 0.3 | Uncertain, potentially outdated |

---

## Source Reliability

Sources are rated based on historical accuracy:

| Rating | Description |
|--------|-------------|
| **Authoritative** | Official product pages, documentation |
| **High** | Product Hunt, established tech blogs |
| **Medium** | Reddit discussions, user reviews |
| **Low** | Random mentions, old posts |
| **Unrated** | New source, no history yet |

---

*Add new terms as they emerge. Keep definitions concise.*
