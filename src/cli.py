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


@scout.command(name="all")
@click.pass_context
def scout_all(ctx):
    """Run all configured scouts."""
    console.print("[bold]Running all scouts...[/bold]")
    console.print()

    # Run Reddit scout
    ctx.invoke(scout_reddit)


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
def curate():
    """Run AI curation on analyzed tools."""
    console.print("[yellow]Curator not yet implemented[/yellow]")


@main.command()
def review():
    """Interactive HITL review interface."""
    db = get_db()
    tools = db.get_tools_by_status("review")

    if not tools:
        console.print("[green]✓[/green] No tools pending review")
        return

    console.print(f"[blue]{len(tools)} tools pending review[/blue]")
    console.print("[yellow]Review interface not yet implemented[/yellow]")


@main.group()
def report():
    """Generate reports and digests."""
    pass


@report.command(name="weekly")
def report_weekly():
    """Generate weekly digest of new and updated tools."""
    console.print("[yellow]Weekly report not yet implemented[/yellow]")


@report.command(name="changelog")
@click.option("--days", "-d", default=7, help="Days of history to include")
def report_changelog(days):
    """Generate changelog of recent updates."""
    db = get_db()
    changes = db.get_recent_changes(days=days)

    if not changes:
        console.print(f"[green]No changes in the last {days} days[/green]")
        return

    table = Table(title=f"Changes (last {days} days)", show_header=True)
    table.add_column("Date", style="dim")
    table.add_column("Tool")
    table.add_column("Change")
    table.add_column("Description")

    for change in changes:
        table.add_row(
            change["detected_at"][:10],
            change["tool_name"],
            change["change_type"],
            change["description"][:50] + "..." if len(change["description"]) > 50 else change["description"]
        )

    console.print(table)


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
