#!/usr/bin/env python3
"""
Glean CLI

Command-line interface for the Glean intelligence gathering system.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.database import Database
from src.config import load_config

console = Console()


def get_db() -> Database:
    """Get database connection using config."""
    config = load_config()
    db_path = config.get("database", {}).get("path", "db/glean.db")
    return Database(db_path)


@click.group()
@click.version_option(version="0.1.0", prog_name="glean")
def main():
    """Glean - AI Sales Tool Intelligence Gathering System

    Discover, analyze, and curate AI tools for sales automation.
    """
    pass


@main.command()
def init():
    """Initialize the database and configuration."""
    db = get_db()
    db.init_schema()
    console.print("[green]✓[/green] Database initialized")

    config_path = Path("config.yaml")
    if not config_path.exists():
        console.print(
            "[yellow]![/yellow] No config.yaml found. "
            "Copy config.example.yaml and add your API keys."
        )
    else:
        console.print("[green]✓[/green] Configuration loaded")


@main.command()
def status():
    """Show pipeline statistics and status."""
    db = get_db()

    try:
        stats = db.get_pipeline_stats()
    except Exception as e:
        console.print(f"[red]Error:[/red] Database not initialized. Run 'glean init' first.")
        return

    # Pipeline status table
    table = Table(title="Pipeline Status", show_header=True, header_style="bold cyan")
    table.add_column("Stage", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Bar", justify="left", width=20)

    statuses = stats["tools_by_status"]
    max_count = max(statuses.values()) if any(statuses.values()) else 1

    stage_colors = {
        "inbox": "yellow",
        "analyzing": "blue",
        "review": "magenta",
        "approved": "green",
        "rejected": "red",
    }

    for stage, count in statuses.items():
        bar_width = int((count / max_count) * 20) if max_count > 0 else 0
        bar = "█" * bar_width + "░" * (20 - bar_width)
        color = stage_colors.get(stage, "white")
        table.add_row(stage.capitalize(), str(count), f"[{color}]{bar}[/{color}]")

    console.print(table)

    # Summary panel
    summary = f"""
[bold]Total Tools:[/bold] {stats['total_tools']}
[bold]Unprocessed Discoveries:[/bold] {stats['unprocessed_discoveries']}
[bold]Total Claims:[/bold] {stats['total_claims']}
[bold]Active Sources:[/bold] {stats['total_sources']}
    """.strip()

    console.print(Panel(summary, title="Summary", border_style="blue"))


@main.group()
def scout():
    """Run scouts to discover new tools."""
    pass


@scout.command(name="reddit")
@click.option("--subreddit", "-s", multiple=True, help="Subreddit to scout")
@click.option("--limit", "-l", default=50, help="Max posts per subreddit")
@click.option("--no-comments", is_flag=True, help="Skip comment extraction")
@click.option("--demo", is_flag=True, help="Use sample data (no Reddit API needed)")
def scout_reddit(subreddit, limit, no_comments, demo):
    """Scout Reddit for AI tool mentions.

    Requires Reddit API credentials in config.yaml, or use --demo for testing.
    """
    from src.scouts.reddit import run_reddit_scout
    from src.config import load_config

    db = get_db()
    db.init_schema()  # Ensure DB is ready

    # Load config for Reddit credentials
    app_config = load_config()
    reddit_creds = app_config.get('api_keys', {}).get('reddit', {})

    config = {
        'reddit': reddit_creds,
        'post_limit': limit,
        'include_comments': not no_comments,
        'demo': demo,
    }
    if subreddit:
        config['subreddits'] = list(subreddit)

    console.print("[bold blue]Starting Reddit scout...[/bold blue]")
    if demo:
        console.print("  Mode: [yellow]Demo (sample data)[/yellow]")
    else:
        console.print(f"  Subreddits: {config.get('subreddits', 'default')}")
        console.print(f"  Post limit: {limit}")
        console.print(f"  Include comments: {not no_comments}")
    console.print()

    try:
        saved, skipped = run_reddit_scout(db, config)
        console.print()
        console.print(f"[green]✓[/green] Scout complete: {saved} new discoveries, {skipped} duplicates skipped")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@scout.command(name="twitter")
@click.option("--query", "-q", multiple=True, help="Custom search query")
@click.option("--limit", "-l", default=100, help="Max results per query")
@click.option("--demo", is_flag=True, help="Use sample data (no Twitter API needed)")
def scout_twitter(query, limit, demo):
    """Scout Twitter/X for AI tool mentions.

    Requires Twitter API Bearer token in config.yaml, or use --demo for testing.
    """
    from src.scouts.twitter import run_twitter_scout
    from src.config import load_config

    db = get_db()
    db.init_schema()

    app_config = load_config()
    twitter_creds = app_config.get('api_keys', {}).get('twitter', {})

    config = {
        'twitter': twitter_creds,
        'max_results': limit,
        'demo': demo,
    }
    if query:
        config['search_queries'] = list(query)

    console.print("[bold blue]Starting Twitter scout...[/bold blue]")
    if demo:
        console.print("  Mode: [yellow]Demo (sample data)[/yellow]")
    else:
        console.print(f"  Max results: {limit}")
    console.print()

    try:
        saved, skipped = run_twitter_scout(db, config)
        console.print()
        console.print(f"[green]✓[/green] Scout complete: {saved} new discoveries, {skipped} duplicates skipped")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@scout.command(name="producthunt")
@click.option("--days", "-d", default=7, help="Days back to search")
@click.option("--min-votes", "-v", default=10, help="Minimum vote count")
@click.option("--demo", is_flag=True, help="Use sample data (no API needed)")
def scout_producthunt(days, min_votes, demo):
    """Scout Product Hunt for AI tool launches.

    Requires Product Hunt API credentials in config.yaml, or use --demo for testing.
    """
    from src.scouts.producthunt import run_producthunt_scout
    from src.config import load_config

    db = get_db()
    db.init_schema()

    app_config = load_config()
    ph_creds = app_config.get('api_keys', {}).get('producthunt', {})

    config = {
        'producthunt': ph_creds,
        'days_back': days,
        'min_votes': min_votes,
        'demo': demo,
    }

    console.print("[bold blue]Starting Product Hunt scout...[/bold blue]")
    if demo:
        console.print("  Mode: [yellow]Demo (sample data)[/yellow]")
    else:
        console.print(f"  Days back: {days}")
        console.print(f"  Min votes: {min_votes}")
    console.print()

    try:
        saved, skipped = run_producthunt_scout(db, config)
        console.print()
        console.print(f"[green]✓[/green] Scout complete: {saved} new discoveries, {skipped} duplicates skipped")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@scout.command(name="web")
@click.option("--query", "-q", multiple=True, help="Custom search query")
@click.option("--results", "-r", default=10, help="Results per query")
@click.option("--demo", is_flag=True, help="Use sample data (no API needed)")
def scout_web(query, results, demo):
    """Scout web search for AI tool mentions.

    Requires SerpAPI or Google Custom Search credentials, or use --demo for testing.
    """
    from src.scouts.websearch import run_websearch_scout
    from src.config import load_config

    db = get_db()
    db.init_schema()

    app_config = load_config()
    serpapi_creds = app_config.get('api_keys', {}).get('serpapi', {})
    google_creds = app_config.get('api_keys', {}).get('google', {})

    config = {
        'serpapi': serpapi_creds,
        'google': google_creds,
        'results_per_query': results,
        'demo': demo,
    }
    if query:
        config['search_queries'] = list(query)

    console.print("[bold blue]Starting Web Search scout...[/bold blue]")
    if demo:
        console.print("  Mode: [yellow]Demo (sample data)[/yellow]")
    else:
        console.print(f"  Results per query: {results}")
    console.print()

    try:
        saved, skipped = run_websearch_scout(db, config)
        console.print()
        console.print(f"[green]✓[/green] Scout complete: {saved} new discoveries, {skipped} duplicates skipped")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@scout.command(name="rss")
@click.option("--feed", "-f", multiple=True, help="RSS feed URL to scout")
@click.option("--days", "-d", default=7, help="Max age of items in days")
@click.option("--demo", is_flag=True, help="Use sample data (no feeds fetched)")
def scout_rss(feed, days, demo):
    """Scout RSS feeds for AI tool mentions.

    Uses default curated feeds, or specify custom feeds with -f.
    No API authentication required.
    """
    from src.scouts.rss import run_rss_scout

    db = get_db()
    db.init_schema()

    config = {
        'max_age_days': days,
        'demo': demo,
    }
    if feed:
        config['feeds'] = [{'name': f, 'url': f, 'category': 'custom'} for f in feed]

    console.print("[bold blue]Starting RSS scout...[/bold blue]")
    if demo:
        console.print("  Mode: [yellow]Demo (sample data)[/yellow]")
    else:
        console.print(f"  Max age: {days} days")
        if feed:
            console.print(f"  Custom feeds: {len(feed)}")
        else:
            console.print("  Using default feeds")
    console.print()

    try:
        saved, skipped = run_rss_scout(db, config)
        console.print()
        console.print(f"[green]✓[/green] Scout complete: {saved} new discoveries, {skipped} duplicates skipped")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@scout.command(name="all")
@click.option("--demo", is_flag=True, help="Use demo mode for all scouts")
@click.pass_context
def scout_all(ctx, demo):
    """Run all configured scouts."""
    console.print("[bold]Running all scouts...[/bold]")
    console.print()

    # Run all scouts
    scouts = [
        ('Reddit', scout_reddit),
        ('Twitter', scout_twitter),
        ('Product Hunt', scout_producthunt),
        ('Web Search', scout_web),
        ('RSS', scout_rss),
    ]

    for name, scout_cmd in scouts:
        console.print(f"[bold cyan]═══ {name} ═══[/bold cyan]")
        try:
            ctx.invoke(scout_cmd, demo=demo)
        except Exception as e:
            console.print(f"[red]Error running {name} scout:[/red] {e}")
        console.print()


@main.command()
@click.option("--limit", "-l", default=10, help="Max discoveries to process")
@click.option("--mock", is_flag=True, help="Use mock analyzer (no API needed)")
def analyze(limit, mock):
    """Process discoveries through analyzers to extract tools and claims.

    Uses Claude API by default. Use --mock for testing without API.
    """
    from src.analyzers import run_analyzer
    from src.config import load_config, get_api_key

    db = get_db()
    discoveries = db.get_unprocessed_discoveries(limit=limit)

    if not discoveries:
        console.print("[green]✓[/green] No unprocessed discoveries")
        return

    console.print(f"[bold blue]Analyzing {len(discoveries)} discoveries...[/bold blue]")

    # Build config
    config = {'limit': limit}

    if not mock:
        app_config = load_config()
        api_key = get_api_key(app_config, 'anthropic')
        if not api_key:
            console.print("[yellow]![/yellow] No Anthropic API key found.")
            console.print("    Set ANTHROPIC_API_KEY env var or add to config.yaml")
            console.print("    Using mock analyzer instead...")
            mock = True
        else:
            config['api_key'] = api_key
            config['model'] = app_config.get('analysis', {}).get('model', 'claude-sonnet-4-20250514')

    if mock:
        console.print("  Mode: [yellow]Mock (pattern matching)[/yellow]")
    else:
        console.print(f"  Mode: [green]Claude API[/green] ({config.get('model', 'default')})")
    console.print()

    try:
        result = run_analyzer(db, config, use_mock=mock)

        console.print()
        console.print(f"[green]✓[/green] Analysis complete:")
        console.print(f"    Processed: {result['processed']} discoveries")
        console.print(f"    Tools extracted: {result['tools_extracted']}")
        console.print(f"    Claims extracted: {result['claims_extracted']}")
        if result['errors']:
            console.print(f"    [red]Errors: {result['errors']}[/red]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@main.command()
@click.option("--min-score", "-m", default=0.3, help="Minimum relevance score for review queue")
@click.option("--no-merge", is_flag=True, help="Don't auto-merge duplicates")
@click.option("--max-queue", default=50, help="Max tools in review queue")
def curate(min_score, no_merge, max_queue):
    """Run AI curation: score tools, deduplicate, and build review queue."""
    from src.curator import run_curation, get_scoring_details

    db = get_db()

    # Check for tools to curate
    tools = db.get_tools_by_status('analyzing')
    if not tools:
        console.print("[green]✓[/green] No tools to curate")
        return

    console.print(f"[bold blue]Curating {len(tools)} tools...[/bold blue]")
    console.print(f"  Min relevance score: {min_score}")
    console.print(f"  Auto-merge duplicates: {not no_merge}")
    console.print()

    result = run_curation(
        db,
        min_relevance=min_score,
        auto_merge_duplicates=not no_merge,
        max_review_queue=max_queue
    )

    console.print(f"[green]✓[/green] Curation complete:")
    console.print(f"    Tools scored: {result.tools_scored}")
    console.print(f"    Promoted to review: [green]{result.tools_promoted}[/green]")
    if result.tools_below_threshold:
        console.print(f"    Below threshold: [yellow]{result.tools_below_threshold}[/yellow]")
    if result.duplicates_found:
        console.print(f"    Duplicates found: {result.duplicates_found}")
        if result.duplicates_merged:
            console.print(f"    Duplicates merged: {result.duplicates_merged}")
    console.print()
    console.print(f"    Score range: {result.min_score:.2f} - {result.max_score:.2f}")
    console.print(f"    Average score: {result.avg_score:.2f}")


@main.command()
def review():
    """Interactive HITL review interface.

    Review tools one by one, approving or rejecting each.
    Commands: [a]pprove, [r]eject, [s]kip, [q]uit
    """
    db = get_db()
    tools = db.get_tools_by_status("review")

    if not tools:
        console.print("[green]✓[/green] No tools pending review")
        return

    # Sort by relevance score descending
    tools.sort(key=lambda t: t.get('relevance_score') or 0, reverse=True)

    console.print(f"[bold blue]Review Queue: {len(tools)} tools[/bold blue]")
    console.print("Commands: [green][a]pprove[/green], [red][r]eject[/red], [yellow][s]kip[/yellow], [dim][q]uit[/dim]")
    console.print()

    approved = 0
    rejected = 0
    skipped = 0

    for i, tool in enumerate(tools):
        # Display tool info
        console.print(f"[bold]─── Tool {i + 1}/{len(tools)} ───[/bold]")
        console.print()

        _display_tool_for_review(db, tool)

        # Get user input
        while True:
            console.print()
            action = console.input("[green]a[/green]pprove / [red]r[/red]eject / [yellow]s[/yellow]kip / [dim]q[/dim]uit: ").strip().lower()

            if action in ('a', 'approve'):
                db.update_tool_status(tool['id'], 'approved')
                # Log the approval in changelog
                db.add_changelog_entry(
                    tool['id'],
                    'new',
                    f"Tool approved for index: {tool['name']}"
                )
                console.print(f"[green]✓ Approved:[/green] {tool['name']}")
                approved += 1
                break

            elif action in ('r', 'reject'):
                reason = console.input("Rejection reason (optional): ").strip()
                db.update_tool_status(tool['id'], 'rejected', rejection_reason=reason or None)
                console.print(f"[red]✗ Rejected:[/red] {tool['name']}")
                rejected += 1
                break

            elif action in ('s', 'skip'):
                console.print(f"[yellow]→ Skipped:[/yellow] {tool['name']}")
                skipped += 1
                break

            elif action in ('q', 'quit'):
                console.print()
                console.print(f"[bold]Session summary:[/bold]")
                console.print(f"  Approved: [green]{approved}[/green]")
                console.print(f"  Rejected: [red]{rejected}[/red]")
                console.print(f"  Skipped: [yellow]{skipped}[/yellow]")
                console.print(f"  Remaining: {len(tools) - i}")
                return

            else:
                console.print("[dim]Invalid input. Use a/r/s/q[/dim]")

        console.print()

    # Final summary
    console.print()
    console.print(f"[bold green]✓ Review complete![/bold green]")
    console.print(f"  Approved: [green]{approved}[/green]")
    console.print(f"  Rejected: [red]{rejected}[/red]")
    console.print(f"  Skipped: [yellow]{skipped}[/yellow]")


def _display_tool_for_review(db, tool):
    """Display a tool's details for review."""
    # Tool header
    score = tool.get('relevance_score')
    score_str = f"{score:.2f}" if score else "N/A"
    score_color = "green" if score and score >= 0.6 else "yellow" if score and score >= 0.4 else "red"

    console.print(f"[bold]{tool['name']}[/bold]  [dim]#{tool['id']}[/dim]")
    console.print(f"  URL: {tool.get('url') or '[dim]N/A[/dim]'}")
    console.print(f"  Category: {tool.get('category') or '[dim]Uncategorized[/dim]'}")
    console.print(f"  Relevance: [{score_color}]{score_str}[/{score_color}]")

    if tool.get('description'):
        console.print(f"  Description: {tool['description'][:100]}{'...' if len(tool.get('description', '')) > 100 else ''}")

    # Show claims
    claims = db.get_claims_for_tool(tool['id'])
    if claims:
        console.print()
        console.print(f"  [bold]Claims ({len(claims)}):[/bold]")
        for claim in claims[:5]:  # Show first 5 claims
            claim_type = claim.get('claim_type', 'unknown')
            content = claim['content'][:80] + ('...' if len(claim['content']) > 80 else '')
            conf = claim.get('confidence', 0)
            console.print(f"    [{claim_type}] {content} [dim]({conf:.0%})[/dim]")
        if len(claims) > 5:
            console.print(f"    [dim]... and {len(claims) - 5} more[/dim]")


@main.command()
def update():
    """Check approved tools for updates and changes.

    Fetches tool webpages and detects pricing, feature, and content changes.
    """
    from src.tracker import run_update_check

    db = get_db()
    db.init_schema()  # Ensure snapshots table exists

    tools = db.get_tools_by_status('approved')
    if not tools:
        console.print("[yellow]![/yellow] No approved tools to check")
        console.print("    Approve some tools first with 'glean review'")
        return

    console.print(f"[bold blue]Checking {len(tools)} approved tools for updates...[/bold blue]")
    console.print()

    try:
        result = run_update_check(db)

        console.print(f"[green]✓[/green] Update check complete:")
        console.print(f"    Tools checked: {result['tools_checked']}")
        console.print(f"    Changes detected: {result['changes_detected']}")

        if result['changes']:
            console.print()
            console.print("[bold]Detected changes:[/bold]")
            for change in result['changes']:
                change_color = {
                    'pricing_change': 'yellow',
                    'feature_added': 'green',
                    'feature_removed': 'red',
                    'news': 'blue',
                    'content_change': 'dim',
                }.get(change.change_type, 'white')

                console.print(f"  [{change_color}]{change.change_type}[/{change_color}] "
                            f"{change.tool_name}: {change.description[:60]}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@main.group()
def report():
    """Generate reports and digests."""
    pass


@report.command(name="weekly")
@click.option("--weeks", "-w", default=1, help="Weeks back to report")
@click.option("--save", "-s", is_flag=True, help="Save to reports/ directory")
def report_weekly(weeks, save):
    """Generate weekly digest of new and updated tools."""
    from src.reporters import generate_weekly_digest, save_report

    db = get_db()

    console.print(f"[bold blue]Generating weekly digest...[/bold blue]")

    report = generate_weekly_digest(db, weeks_back=weeks)

    if save:
        from datetime import datetime
        filename = f"weekly-digest-{datetime.now().strftime('%Y-%m-%d')}.md"
        path = save_report(report, filename)
        console.print(f"[green]✓[/green] Saved to {path}")
    else:
        console.print()
        console.print(report)


@report.command(name="changelog")
@click.option("--days", "-d", default=7, help="Days of history to include")
@click.option("--save", "-s", is_flag=True, help="Save to reports/ directory")
def report_changelog(days, save):
    """Generate changelog of recent updates."""
    from src.reporters import generate_changelog, save_report

    db = get_db()

    console.print(f"[bold blue]Generating changelog...[/bold blue]")

    report = generate_changelog(db, days=days)

    if save:
        from datetime import datetime
        filename = f"changelog-{datetime.now().strftime('%Y-%m-%d')}.md"
        path = save_report(report, filename)
        console.print(f"[green]✓[/green] Saved to {path}")
    else:
        console.print()
        console.print(report)


@report.command(name="index")
@click.option("--save", "-s", is_flag=True, help="Save to reports/ directory")
def report_index(save):
    """Generate index of all approved tools."""
    from src.reporters import generate_tools_index, save_report

    db = get_db()

    console.print(f"[bold blue]Generating tools index...[/bold blue]")

    report = generate_tools_index(db)

    if save:
        from datetime import datetime
        filename = f"tools-index-{datetime.now().strftime('%Y-%m-%d')}.md"
        path = save_report(report, filename)
        console.print(f"[green]✓[/green] Saved to {path}")
    else:
        console.print()
        console.print(report)


@main.group()
def migrate():
    """Database migration commands."""
    pass


@migrate.command(name="status")
def migrate_status():
    """Show migration status."""
    from src.migrations import Migrator

    config = load_config()
    db_path = config.get("database", {}).get("path", "db/glean.db")
    migrator = Migrator(db_path)

    try:
        status = migrator.status()

        console.print("[bold]Migration Status[/bold]")
        console.print()

        if status["applied"]:
            console.print(f"[green]Applied ({status['total_applied']}):[/green]")
            for name in status["applied"]:
                console.print(f"  [green]✓[/green] {name}")
        else:
            console.print("[dim]No migrations applied yet[/dim]")

        if status["pending"]:
            console.print()
            console.print(f"[yellow]Pending ({status['total_pending']}):[/yellow]")
            for name in status["pending"]:
                console.print(f"  [yellow]○[/yellow] {name}")

    finally:
        migrator.close()


@migrate.command(name="run")
@click.option("--steps", "-n", type=int, help="Number of migrations to run")
def migrate_run(steps):
    """Apply pending migrations."""
    from src.migrations import Migrator

    config = load_config()
    db_path = config.get("database", {}).get("path", "db/glean.db")
    migrator = Migrator(db_path)

    try:
        pending = migrator.get_pending_migrations()
        if not pending:
            console.print("[green]✓[/green] No pending migrations")
            return

        console.print(f"[bold blue]Applying {len(pending) if steps is None else min(steps, len(pending))} migration(s)...[/bold blue]")

        applied = migrator.migrate(steps)

        for name in applied:
            console.print(f"  [green]✓[/green] Applied: {name}")

        console.print()
        console.print(f"[green]✓[/green] {len(applied)} migration(s) applied")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
    finally:
        migrator.close()


@migrate.command(name="rollback")
@click.option("--steps", "-n", type=int, default=1, help="Number of migrations to rollback")
@click.confirmation_option(prompt="Are you sure you want to rollback?")
def migrate_rollback(steps):
    """Rollback applied migrations."""
    from src.migrations import Migrator

    config = load_config()
    db_path = config.get("database", {}).get("path", "db/glean.db")
    migrator = Migrator(db_path)

    try:
        applied = migrator.get_applied_migrations()
        if not applied:
            console.print("[yellow]![/yellow] No migrations to rollback")
            return

        console.print(f"[bold yellow]Rolling back {min(steps, len(applied))} migration(s)...[/bold yellow]")

        rolled_back = migrator.rollback(steps)

        for name in rolled_back:
            console.print(f"  [yellow]↩[/yellow] Rolled back: {name}")

        console.print()
        console.print(f"[yellow]![/yellow] {len(rolled_back)} migration(s) rolled back")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
    finally:
        migrator.close()


@migrate.command(name="create")
@click.argument("name")
@click.option("--table", "-t", is_flag=True, help="Use table creation template")
def migrate_create(name, table):
    """Create a new migration file."""
    from src.migrations import create_migration

    template = "table" if table else "default"

    try:
        path = create_migration(name, template=template)
        console.print(f"[green]✓[/green] Created migration: {path}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@migrate.command(name="reset")
@click.confirmation_option(prompt="This will rollback ALL migrations. Are you sure?")
def migrate_reset():
    """Rollback all migrations."""
    from src.migrations import Migrator

    config = load_config()
    db_path = config.get("database", {}).get("path", "db/glean.db")
    migrator = Migrator(db_path)

    try:
        applied = migrator.get_applied_migrations()
        if not applied:
            console.print("[yellow]![/yellow] No migrations to reset")
            return

        console.print(f"[bold red]Resetting {len(applied)} migration(s)...[/bold red]")

        rolled_back = migrator.reset()

        for name in rolled_back:
            console.print(f"  [red]↩[/red] Rolled back: {name}")

        console.print()
        console.print(f"[red]![/red] Database reset ({len(rolled_back)} migrations rolled back)")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
    finally:
        migrator.close()


@main.command()
@click.argument("tool_id", type=int)
def show(tool_id):
    """Show details for a specific tool."""
    db = get_db()
    tool = db.get_tool(tool_id)

    if not tool:
        console.print(f"[red]Tool {tool_id} not found[/red]")
        return

    # Tool info panel
    info = f"""
[bold]Name:[/bold] {tool['name']}
[bold]URL:[/bold] {tool['url'] or 'N/A'}
[bold]Category:[/bold] {tool['category'] or 'Uncategorized'}
[bold]Status:[/bold] {tool['status']}
[bold]Relevance:[/bold] {tool['relevance_score'] or 'Not scored'}
[bold]Created:[/bold] {tool['created_at']}
    """.strip()

    status_color = {
        "inbox": "yellow",
        "analyzing": "blue",
        "review": "magenta",
        "approved": "green",
        "rejected": "red",
    }.get(tool["status"], "white")

    console.print(Panel(info, title=f"Tool #{tool_id}", border_style=status_color))

    if tool["description"]:
        console.print(Panel(tool["description"], title="Description"))

    # Claims
    claims = db.get_claims_for_tool(tool_id)
    if claims:
        table = Table(title="Claims", show_header=True)
        table.add_column("Type")
        table.add_column("Claim")
        table.add_column("Confidence", justify="right")
        table.add_column("Source")

        for claim in claims:
            conf_color = "green" if claim["confidence"] >= 0.7 else "yellow" if claim["confidence"] >= 0.4 else "red"
            table.add_row(
                claim["claim_type"] or "-",
                claim["content"][:60] + "..." if len(claim["content"]) > 60 else claim["content"],
                f"[{conf_color}]{claim['confidence']:.2f}[/{conf_color}]",
                claim["source_name"]
            )

        console.print(table)


if __name__ == "__main__":
    main()
