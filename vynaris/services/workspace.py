from __future__ import annotations

import uuid
from pathlib import Path

from vynaris.config import get_settings

settings = get_settings()


def workspace_root(person_id: uuid.UUID | str) -> Path:
    p = settings.workspaces_dir / str(person_id)
    return p


def ensure_workspace(person_id: uuid.UUID | str) -> Path:
    root = workspace_root(person_id)
    (root / "private").mkdir(parents=True, exist_ok=True)
    (root / "public").mkdir(parents=True, exist_ok=True)
    (root / "skills").mkdir(parents=True, exist_ok=True)
    for fname in ("memory.md", "plan.md", "todo.md"):
        fp = root / fname
        if not fp.exists():
            fp.write_text(_initial_content(fname), encoding="utf-8")
    return root


def _initial_content(fname: str) -> str:
    if fname == "memory.md":
        return "# Memory\n\nLong-term notes your agent will remember across sessions.\n"
    if fname == "plan.md":
        return "# Plan\n\nYour agent writes its current plan here.\n"
    if fname == "todo.md":
        return "# Todo\n\n- [ ] (agent will populate)\n"
    return ""


def safe_relative(root: Path, subpath: str) -> Path:
    """Resolve subpath inside root; reject traversal."""
    target = (root / subpath).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise ValueError(f"path escapes workspace: {subpath}")
    return target
