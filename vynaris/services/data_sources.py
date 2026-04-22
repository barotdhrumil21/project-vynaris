"""Data-source introspection — make the measurement plumbing visible.

The UI uses these helpers to show, for every non-manual KR:
  - the raw file/URL/expression the scheduler reads
  - a preview (first rows of CSV, etc.)
  - a value history from ``kr_value_changed`` system events (used for sparklines)
  - a freshness status (fresh / stale / never / failed)
"""

from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db.models import Goal, KeyResult, Message
from vynaris.services.kr_refresh import _cadence_minutes
from vynaris.services.workspace import safe_relative, workspace_root


# ── value history (from kr_value_changed events) ──────────────────────────────


@dataclass(frozen=True)
class HistoryPoint:
    at: datetime
    value: float
    info: str


async def kr_value_history(
    db: AsyncSession, *, kr_id: uuid.UUID, goal: Goal, limit: int = 24,
) -> list[HistoryPoint]:
    """Return value timeline for a KR, oldest first."""
    if goal.channel_id is None:
        return []
    rows = (
        await db.execute(
            select(Message)
            .where(
                Message.channel_id == goal.channel_id,
                Message.kind == "system_event",
            )
            .order_by(Message.created_at.desc())
            .limit(200)
        )
    ).scalars().all()
    kr_key = str(kr_id)
    history: list[HistoryPoint] = []
    for m in rows:
        extra = m.extra or {}
        if extra.get("event") != "kr_value_changed":
            continue
        if str(extra.get("kr_id") or "") != kr_key:
            continue
        to_val = extra.get("to")
        try:
            v = float(to_val)
        except (TypeError, ValueError):
            continue
        history.append(HistoryPoint(at=m.created_at, value=v, info=str(extra.get("info") or "")))
        if len(history) >= limit:
            break
    history.reverse()
    return history


def sparkline_svg(points: list[HistoryPoint], *, width: int = 120, height: int = 28) -> str:
    """Tiny inline SVG sparkline for KR cards. Empty string if not enough data."""
    if len(points) < 2:
        return ""
    values = [p.value for p in points]
    lo = min(values)
    hi = max(values)
    span = (hi - lo) or 1.0
    dx = width / (len(points) - 1)
    coords: list[str] = []
    for i, v in enumerate(values):
        x = i * dx
        y = height - ((v - lo) / span) * (height - 4) - 2
        coords.append(f"{x:.1f},{y:.1f}")
    last_x, last_y = map(float, coords[-1].split(","))
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        f'<polyline points="{" ".join(coords)}" fill="none" '
        f'stroke="currentColor" stroke-width="1.5" opacity="0.75"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2" fill="currentColor"/>'
        f"</svg>"
    )


# ── source preview (CSV rows, URL samples, formula inputs) ─────────────────────


@dataclass(frozen=True)
class SourcePreview:
    kind: str                          # workspace_file | url | formula | manual
    summary: str                       # human-readable one-liner
    path_or_url: str                   # the configured location
    rows: list[list[str]]              # CSV rows (header + last N) for workspace_file
    error: str                         # non-empty if reading failed


def _csv_tail(path: Path, n: int = 6) -> tuple[list[list[str]], str]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            rows = [r for r in csv.reader(f) if r]
    except FileNotFoundError:
        return [], f"file not found: {path.name}"
    except Exception as e:
        return [], f"read error: {e}"
    if not rows:
        return [], "file is empty"
    header = rows[0]
    tail = rows[1:][-n:]
    return [header] + tail, ""


def kr_source_preview(kr: KeyResult, goal: Goal) -> SourcePreview:
    cfg = kr.measurement_config or {}
    if kr.measurement_kind == "manual":
        return SourcePreview(
            kind="manual", summary="Manual — updated by the owner", path_or_url="", rows=[], error="",
        )
    if kr.measurement_kind == "workspace_file":
        rel = str(cfg.get("path") or "")
        if not rel:
            return SourcePreview(kind="workspace_file", summary="(no path configured)", path_or_url="", rows=[], error="missing path")
        try:
            root = workspace_root(goal.owner_id)
            target = safe_relative(root, rel)
        except Exception as e:
            return SourcePreview(kind="workspace_file", summary=rel, path_or_url=rel, rows=[], error=f"path error: {e}")
        if not target.exists():
            return SourcePreview(kind="workspace_file", summary=rel, path_or_url=rel, rows=[], error="file not found")
        if target.suffix.lower() == ".csv":
            rows, err = _csv_tail(target, n=6)
            col = cfg.get("column")
            summary = f"{rel}" + (f" · column {col!r}" if col else "")
            return SourcePreview(kind="workspace_file", summary=summary, path_or_url=rel, rows=rows, error=err)
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return SourcePreview(kind="workspace_file", summary=rel, path_or_url=rel, rows=[], error=str(e))
        preview = text.splitlines()[-6:]
        return SourcePreview(
            kind="workspace_file", summary=f"{rel} (text)", path_or_url=rel,
            rows=[[ln] for ln in preview], error="",
        )
    if kr.measurement_kind == "url":
        url = str(cfg.get("url") or "")
        jp = str(cfg.get("json_path") or "")
        summary = url + (f" · {jp}" if jp else "")
        return SourcePreview(kind="url", summary=summary, path_or_url=url, rows=[], error="")
    if kr.measurement_kind == "formula":
        expr = str(cfg.get("expr") or cfg.get("formula") or "")
        return SourcePreview(kind="formula", summary=f"= {expr}", path_or_url="", rows=[], error="")
    return SourcePreview(kind=kr.measurement_kind, summary="(unknown kind)", path_or_url="", rows=[], error="")


# ── freshness status ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Freshness:
    status: str                        # fresh | stale | never | manual
    label: str                         # short display label
    next_refresh_in_minutes: int | None


def kr_freshness(kr: KeyResult) -> Freshness:
    if kr.measurement_kind == "manual":
        return Freshness(status="manual", label="manual", next_refresh_in_minutes=None)
    if kr.last_updated_at is None:
        return Freshness(status="never", label="never refreshed", next_refresh_in_minutes=0)
    cadence = _cadence_minutes(kr)
    elapsed = datetime.now(timezone.utc) - kr.last_updated_at
    minutes = int(elapsed.total_seconds() // 60)
    if minutes >= cadence:
        return Freshness(status="stale", label=f"stale by {minutes - cadence}m", next_refresh_in_minutes=0)
    remaining = cadence - minutes
    return Freshness(status="fresh", label=f"fresh · next in {remaining}m", next_refresh_in_minutes=remaining)
