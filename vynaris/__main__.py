from __future__ import annotations

import asyncio
import os
import secrets
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    help="Vynaris — enterprise agentic work OS",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def _ok(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def _info(msg: str) -> None:
    console.print(f"[cyan]→[/cyan] {msg}")


def _warn(msg: str) -> None:
    console.print(f"[yellow]![/yellow] {msg}")


def _err(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")


def _banner() -> None:
    console.print(Panel.fit(
        "[bold]Vynaris[/bold]  [dim]enterprise agentic work OS[/dim]",
        border_style="magenta", padding=(0, 2),
    ))


def _env_path() -> Path:
    return Path.cwd() / ".env"


def _write_env(values: dict[str, str]) -> None:
    lines = []
    for k, v in values.items():
        lines.append(f"{k}={v}")
    _env_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_env() -> dict[str, str]:
    p = _env_path()
    if not p.exists():
        return {}
    out: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


@app.command()
def setup(
    api_key: str = typer.Option(None, "--api-key", help="Anthropic API key (sk-ant-...)"),
    skip_prompts: bool = typer.Option(False, "--yes", "-y", help="Skip interactive prompts"),
) -> None:
    """First-time setup: write .env, bootstrap DB, seed demo data."""
    _banner()
    env = _read_env()

    if not api_key:
        api_key = env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or ""
        if not api_key and not skip_prompts:
            api_key = typer.prompt(
                "Anthropic API key (sk-ant-...) — leave blank to use your Claude CLI subscription",
                hide_input=True, default="",
            )

    if not api_key:
        claude_present = bool(shutil.which("claude"))
        if claude_present:
            _ok("no API key — will use your Claude CLI subscription auth")
        else:
            _warn("No API key and no Claude CLI. Install one: npm install -g @anthropic-ai/claude-code && claude login")

    secret = env.get("VYNARIS_SECRET_KEY") or secrets.token_urlsafe(48)

    new_env = {
        "ANTHROPIC_API_KEY": api_key or "",
        "DATABASE_URL": env.get("DATABASE_URL", "postgresql+asyncpg://vynaris:vynaris_dev_password_change_me@localhost:5432/vynaris"),
        "VYNARIS_HOST": env.get("VYNARIS_HOST", "127.0.0.1"),
        "VYNARIS_PORT": env.get("VYNARIS_PORT", "7878"),
        "VYNARIS_SECRET_KEY": secret,
        "VYNARIS_DATA_DIR": env.get("VYNARIS_DATA_DIR", "./vynaris-data"),
        "VYNARIS_ENV": env.get("VYNARIS_ENV", "dev"),
        "VYNARIS_MODEL": env.get("VYNARIS_MODEL", "claude-sonnet-4-5"),
    }
    _write_env(new_env)
    _ok("wrote .env")

    _info("bootstrapping database...")
    from vynaris.db.bootstrap import create_all
    from vynaris.db.seed import maybe_seed_demo
    asyncio.run(_bootstrap_and_seed(create_all, maybe_seed_demo))
    _ok("database ready")

    _ok("setup complete")
    console.print()
    console.print("  Next: [bold]vynaris start[/bold]  then  [bold]vynaris open[/bold]")
    console.print()


async def _bootstrap_and_seed(create_all, maybe_seed) -> None:
    await create_all()
    await maybe_seed()


@app.command()
def start(
    host: str = typer.Option(None, help="Host to bind (default from .env)"),
    port: int = typer.Option(None, help="Port (default from .env)"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev)"),
) -> None:
    """Start the Vynaris server."""
    env = _read_env()
    h = host or env.get("VYNARIS_HOST", "127.0.0.1")
    p = port or int(env.get("VYNARIS_PORT", "7878") or 7878)
    for k, v in env.items():
        os.environ.setdefault(k, v)
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass
    console.print(f"[magenta]Vynaris[/magenta] on [bold]http://{h}:{p}[/bold]  (ctrl+c to stop)")
    import uvicorn
    uvicorn.run(
        "vynaris.app:app",
        host=h, port=p, reload=reload, log_level="info",
        loop="asyncio",
    )


@app.command()
def open(host: str = typer.Option(None), port: int = typer.Option(None)) -> None:
    """Open Vynaris in your browser."""
    env = _read_env()
    h = host or env.get("VYNARIS_HOST", "127.0.0.1")
    p = port or int(env.get("VYNARIS_PORT", "7878") or 7878)
    url = f"http://{h}:{p}"
    _info(f"opening {url}")
    webbrowser.open(url)


@app.command()
def status() -> None:
    """Show status: env, db, running server."""
    _banner()
    env = _read_env()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="dim")
    t.add_column()
    t.add_row(".env", "present ✓" if _env_path().exists() else "missing ✗")
    t.add_row("API key", "set ✓" if env.get("ANTHROPIC_API_KEY") else "[yellow]not set[/yellow]")
    t.add_row("db url", env.get("DATABASE_URL", "(default)"))
    t.add_row("host:port", f"{env.get('VYNARIS_HOST', '127.0.0.1')}:{env.get('VYNARIS_PORT', '7878')}")
    claude = shutil.which("claude")
    t.add_row("claude CLI", f"{claude} ✓" if claude else "[red]not found — agent will not work[/red]")
    console.print(t)
    console.print()
    _check_db()


def _check_db() -> None:
    try:
        asyncio.run(_ping_db())
        _ok("database reachable")
    except Exception as e:
        _err(f"database not reachable: {e}")


async def _ping_db() -> None:
    from sqlalchemy import text
    from vynaris.db.session import engine
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))


@app.command()
def reset(yes: bool = typer.Option(False, "--yes", "-y")) -> None:
    """Drop all data and return to a fresh install. Destructive."""
    if not yes:
        if not typer.confirm("This wipes ALL org data (users, channels, messages, goals, workspaces). Continue?"):
            _info("aborted")
            return
    from vynaris.db.bootstrap import create_all, drop_all
    async def _go():
        await drop_all()
        await create_all()
    asyncio.run(_go())
    data = Path(_read_env().get("VYNARIS_DATA_DIR", "./vynaris-data"))
    workspaces = data / "workspaces"
    if workspaces.exists():
        shutil.rmtree(workspaces, ignore_errors=True)
    _ok("reset complete — open the app to run through /setup again")


@app.command("reset-password")
def reset_password(email: str = typer.Argument(...), password: str = typer.Option(None, prompt=True, hide_input=True, confirmation_prompt=True)) -> None:
    """Reset a user's password (no UI for this yet, use the CLI)."""
    import asyncio
    from sqlalchemy import select
    from vynaris.auth import hash_password
    from vynaris.db.models import Person
    from vynaris.db.session import AsyncSessionLocal

    async def _go():
        async with AsyncSessionLocal() as s:
            p = (await s.execute(select(Person).where(Person.email == email.strip().lower()))).scalar_one_or_none()
            if p is None:
                _err(f"no user with email {email}")
                return False
            p.password_hash = hash_password(password)
            await s.commit()
            return True
    ok = asyncio.run(_go())
    if ok:
        _ok(f"password reset for {email}")


@app.command("seed-credit-risk")
def seed_credit_risk(email: str = typer.Argument(..., help="Owner of the demo goal")) -> None:
    """Seed a Credit Risk demo goal + CSV in the owner's workspace (Batch 1 demo)."""
    _banner()
    from vynaris.seed_demo import seed_credit_risk_demo
    asyncio.run(seed_credit_risk_demo(email.strip().lower(), console))


@app.command()
def doctor() -> None:
    """Diagnose install issues."""
    _banner()
    any_issue = False

    if sys.version_info < (3, 11):
        _err(f"python too old: {sys.version.split()[0]} (need 3.11+)")
        any_issue = True
    else:
        _ok(f"python {sys.version.split()[0]}")

    try:
        import claude_agent_sdk  # noqa: F401
        _ok("claude-agent-sdk installed")
    except ImportError:
        _err("claude-agent-sdk not installed — run: pip install claude-agent-sdk")
        any_issue = True

    if shutil.which("claude"):
        _ok("claude CLI installed")
    else:
        _err("claude CLI missing — run: npm install -g @anthropic-ai/claude-code")
        any_issue = True

    if _env_path().exists():
        _ok(".env present")
        env = _read_env()
        if env.get("ANTHROPIC_API_KEY"):
            _ok("ANTHROPIC_API_KEY set")
        else:
            _warn("ANTHROPIC_API_KEY not set in .env")
    else:
        _warn(".env missing — run: vynaris setup")

    try:
        asyncio.run(_ping_db())
        _ok("database reachable")
    except Exception as e:
        _err(f"database unreachable: {e}")
        any_issue = True

    if any_issue:
        _warn("some issues detected")
    else:
        _ok("all checks passed")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
