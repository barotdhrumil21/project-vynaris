from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def ctx(request: Request, **extra) -> dict:
    base = {"request": request}
    base.update(extra)
    return base


def render(request: Request, name: str, **context):
    from vynaris.config import get_settings
    settings = get_settings()
    context.setdefault("viewer", None)
    context.setdefault("agent_available", _agent_available(settings))
    context.setdefault("model_name", settings.vynaris_model)
    return templates.TemplateResponse(request, name, context)


def _agent_available(settings) -> bool:
    """Agent is available if API key is set, OR if the Claude CLI is logged in (uses subscription auth)."""
    if settings.anthropic_api_key:
        return True
    import shutil, subprocess
    if not shutil.which("claude"):
        try:
            from claude_agent_sdk._internal.transport.subprocess_cli import _find_cli  # noqa
            return True
        except Exception:
            return False
    return True


def _initials(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _friendly_status(status: str) -> str:
    return {
        "not_started": "Not started",
        "in_progress": "In progress",
        "blocked": "Blocked",
        "completed": "Completed",
        "cancelled": "Cancelled",
    }.get(status, status.replace("_", " ").title())


def _status_color(status: str) -> str:
    return {
        "not_started": "slate",
        "in_progress": "indigo",
        "blocked": "amber",
        "completed": "emerald",
        "cancelled": "stone",
    }.get(status, "slate")


def _friendly_kind(kind: str) -> str:
    return {
        "agent_action": "Agent action",
        "goal_update": "Goal update",
        "artifact_created": "Artifact",
        "chat_message": "Chat",
        "org_broadcast": "Announcement",
    }.get(kind, kind.replace("_", " ").title())


def _humanize_ts(ts) -> str:
    if ts is None:
        return ""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    delta = now - ts if ts.tzinfo else now.replace(tzinfo=None) - ts
    secs = int(delta.total_seconds())
    if secs < 10:
        return "just now"
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    if secs < 86400 * 7:
        return f"{secs // 86400}d ago"
    return ts.strftime("%b %d")


templates.env.filters["initials"] = _initials
templates.env.filters["friendly_status"] = _friendly_status
templates.env.filters["status_color"] = _status_color
templates.env.filters["friendly_kind"] = _friendly_kind
templates.env.filters["humanize_ts"] = _humanize_ts
