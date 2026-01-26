#!/usr/bin/env python3
"""
Database migration runner for Supabase.

Connects directly to the Supabase PostgreSQL database and runs
SQL migration files from the migrations/ directory.

Usage:
    uv run python run_migrations.py                    # Run pending migrations
    uv run python run_migrations.py --status           # Show migration status
    uv run python run_migrations.py --dry-run          # Show what would run
    uv run python run_migrations.py --force 001        # Force re-run a migration

Configuration:
    Set PRIZMS_SUPABASE_DB_URL in your .env file:
    PRIZMS_SUPABASE_DB_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

    Find this in Supabase Dashboard → Settings → Database → Connection string → URI
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2 import sql
from rich.console import Console
from rich.table import Table

from api.config import get_settings

console = Console()

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATIONS_TABLE = "_migrations"


def get_db_connection():
    """Get a connection to the Supabase PostgreSQL database."""
    settings = get_settings()
    
    if not settings.supabase_db_url:
        console.print("[red]Error:[/red] PRIZMS_SUPABASE_DB_URL is not set.")
        console.print()
        console.print("Set it in your .env file:")
        console.print("  PRIZMS_SUPABASE_DB_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres")
        console.print()
        console.print("Find this in Supabase Dashboard → Settings → Database → Connection string → URI")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(settings.supabase_db_url)
        return conn
    except psycopg2.Error as e:
        console.print(f"[red]Database connection failed:[/red] {e}")
        sys.exit(1)


def ensure_migrations_table(conn):
    """Create the migrations tracking table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                checksum VARCHAR(64) NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        conn.commit()


def get_applied_migrations(conn) -> dict[str, dict]:
    """Get list of already applied migrations."""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT name, checksum, applied_at 
            FROM {MIGRATIONS_TABLE} 
            ORDER BY name;
        """)
        return {
            row[0]: {"checksum": row[1], "applied_at": row[2]}
            for row in cur.fetchall()
        }


def get_pending_migrations(conn) -> list[tuple[str, Path, str]]:
    """Get list of pending migrations to run."""
    applied = get_applied_migrations(conn)
    pending = []
    
    if not MIGRATIONS_DIR.exists():
        console.print(f"[yellow]Warning:[/yellow] Migrations directory not found: {MIGRATIONS_DIR}")
        return []
    
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        name = sql_file.name
        content = sql_file.read_text()
        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        if name not in applied:
            pending.append((name, sql_file, checksum))
        elif applied[name]["checksum"] != checksum:
            console.print(f"[yellow]Warning:[/yellow] Migration {name} has changed since it was applied!")
    
    return pending


def run_migration(conn, name: str, sql_file: Path, checksum: str, dry_run: bool = False):
    """Run a single migration file."""
    content = sql_file.read_text()
    
    if dry_run:
        console.print(f"[cyan]Would run:[/cyan] {name}")
        return
    
    console.print(f"[blue]Running:[/blue] {name}...")
    
    try:
        with conn.cursor() as cur:
            # Run the migration
            cur.execute(content)
            
            # Record it in the migrations table
            cur.execute(
                sql.SQL("INSERT INTO {} (name, checksum) VALUES (%s, %s)").format(
                    sql.Identifier(MIGRATIONS_TABLE)
                ),
                (name, checksum)
            )
        
        conn.commit()
        console.print(f"[green]✓[/green] {name} applied successfully")
        
    except psycopg2.Error as e:
        conn.rollback()
        console.print(f"[red]✗[/red] {name} failed: {e}")
        raise


def show_status(conn):
    """Show the status of all migrations."""
    applied = get_applied_migrations(conn)
    pending = get_pending_migrations(conn)
    
    table = Table(title="Migration Status")
    table.add_column("Migration", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Applied At")
    table.add_column("Checksum")
    
    # Show applied migrations
    for name, info in applied.items():
        table.add_row(
            name,
            "[green]Applied[/green]",
            info["applied_at"].strftime("%Y-%m-%d %H:%M:%S") if info["applied_at"] else "",
            info["checksum"]
        )
    
    # Show pending migrations
    for name, _, checksum in pending:
        table.add_row(
            name,
            "[yellow]Pending[/yellow]",
            "",
            checksum
        )
    
    if not applied and not pending:
        console.print("[dim]No migrations found.[/dim]")
    else:
        console.print(table)


def force_migration(conn, migration_prefix: str):
    """Force re-run a specific migration."""
    # Find the migration file
    matches = list(MIGRATIONS_DIR.glob(f"{migration_prefix}*.sql"))
    
    if not matches:
        console.print(f"[red]Error:[/red] No migration found matching '{migration_prefix}'")
        sys.exit(1)
    
    if len(matches) > 1:
        console.print(f"[red]Error:[/red] Multiple migrations match '{migration_prefix}':")
        for m in matches:
            console.print(f"  - {m.name}")
        sys.exit(1)
    
    sql_file = matches[0]
    name = sql_file.name
    content = sql_file.read_text()
    checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    console.print(f"[yellow]Warning:[/yellow] Force re-running migration: {name}")
    console.print("This will execute the migration SQL again, which may cause errors if the schema already exists.")
    
    response = input("Continue? [y/N] ")
    if response.lower() != "y":
        console.print("Aborted.")
        return
    
    # Remove from tracking table if exists
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("DELETE FROM {} WHERE name = %s").format(
                sql.Identifier(MIGRATIONS_TABLE)
            ),
            (name,)
        )
    conn.commit()
    
    # Run the migration
    run_migration(conn, name, sql_file, checksum)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run database migrations for Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python run_migrations.py          Run all pending migrations
  uv run python run_migrations.py --status Show migration status
  uv run python run_migrations.py --dry-run Show what would run
  uv run python run_migrations.py --force 001 Force re-run migration 001
        """
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show migration status without running anything"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what migrations would run without executing them"
    )
    parser.add_argument(
        "--force",
        metavar="PREFIX",
        help="Force re-run a specific migration by prefix (e.g., '001')"
    )
    
    args = parser.parse_args()
    
    console.print("[bold]Prizms Database Migrations[/bold]")
    console.print()
    
    conn = get_db_connection()
    ensure_migrations_table(conn)
    
    try:
        if args.status:
            show_status(conn)
        elif args.force:
            force_migration(conn, args.force)
        else:
            pending = get_pending_migrations(conn)
            
            if not pending:
                console.print("[green]All migrations are up to date![/green]")
                return
            
            console.print(f"Found {len(pending)} pending migration(s):")
            for name, _, _ in pending:
                console.print(f"  - {name}")
            console.print()
            
            for name, sql_file, checksum in pending:
                run_migration(conn, name, sql_file, checksum, dry_run=args.dry_run)
            
            if not args.dry_run:
                console.print()
                console.print("[green]All migrations completed successfully![/green]")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
