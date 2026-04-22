"""KR data-source reality: read workspace files, poll URLs, evaluate formulas,
update KR current_value, emit kr_value_changed system events."""

from __future__ import annotations

import ast
import csv
import logging
import operator
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db.models import Goal, KeyResult
from vynaris.db.session import AsyncSessionLocal
from vynaris.services.goals import post_system_event
from vynaris.services.workspace import safe_relative, workspace_root

log = logging.getLogger("vynaris.kr_refresh")


# ── cadence ────────────────────────────────────────────────────────────────

def _cadence_minutes(kr: KeyResult) -> int:
    cfg = kr.measurement_config or {}
    raw = cfg.get("cadence_minutes")
    try:
        v = int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        v = 0
    if v <= 0:
        # kind-specific defaults
        if kr.measurement_kind == "url":
            return 360  # 6h
        if kr.measurement_kind == "formula":
            return 5
        return 1440  # workspace file: daily
    return max(v, 1)


def _is_due(kr: KeyResult) -> bool:
    if kr.measurement_kind not in ("workspace_file", "url", "formula"):
        return False
    if kr.last_updated_at is None:
        return True
    delta = datetime.now(timezone.utc) - kr.last_updated_at
    return delta >= timedelta(minutes=_cadence_minutes(kr))


# ── workspace_file ─────────────────────────────────────────────────────────

def _read_csv_value(path: Path, cfg: dict[str, Any]) -> float | None:
    """Extract a numeric value from a CSV given {column, row}.
    Defaults: last row, first numeric column."""
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = [r for r in reader if r]
    if not rows:
        return None
    header = rows[0]
    data = rows[1:] if len(rows) > 1 else []

    col_spec = cfg.get("column")
    row_spec = cfg.get("row", "last")

    col_idx: int | None = None
    if col_spec:
        try:
            col_idx = int(col_spec)
        except (TypeError, ValueError):
            # treat as header name
            low = [h.strip().lower() for h in header]
            needle = str(col_spec).strip().lower()
            if needle in low:
                col_idx = low.index(needle)

    # Determine target row(s)
    if not data:
        target_rows = [header]
    elif row_spec == "first":
        target_rows = [data[0]]
    elif isinstance(row_spec, int) or (isinstance(row_spec, str) and row_spec.lstrip("-").isdigit()):
        i = int(row_spec)
        target_rows = [data[i]] if -len(data) <= i < len(data) else [data[-1]]
    else:
        target_rows = [data[-1]]

    row = target_rows[0]
    if col_idx is not None and 0 <= col_idx < len(row):
        return _to_float(row[col_idx])
    # fallback: first numeric cell in the row
    for cell in row:
        v = _to_float(cell)
        if v is not None:
            return v
    return None


def _read_text_file_value(path: Path, cfg: dict[str, Any]) -> float | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = cfg.get("regex")
    if pattern:
        m = re.search(pattern, text)
        if m:
            grp = m.group(1) if m.groups() else m.group(0)
            return _to_float(grp)
        return None
    # fallback: first number in the file
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return _to_float(m.group(0)) if m else None


def _read_workspace_file_value(owner_id: uuid.UUID, cfg: dict[str, Any]) -> tuple[float | None, str]:
    rel = (cfg.get("path") or "").strip()
    if not rel:
        return None, "missing path"
    try:
        root = workspace_root(owner_id)
        target = safe_relative(root, rel)
    except Exception as e:
        return None, f"path error: {e}"
    if not target.exists() or not target.is_file():
        return None, f"file not found: {rel}"
    try:
        suffix = target.suffix.lower()
        if suffix == ".csv":
            v = _read_csv_value(target, cfg)
        else:
            v = _read_text_file_value(target, cfg)
        if v is None:
            return None, "no numeric value extracted"
        return v, f"read {rel}"
    except Exception as e:
        return None, f"read error: {e}"


# ── url ────────────────────────────────────────────────────────────────────

def _json_path_lookup(obj: Any, path: str) -> Any:
    """Simple dotted path: $.a.b[0].c → a.b.0.c. No filters, just keys + indices."""
    if not path:
        return obj
    p = path.strip()
    if p.startswith("$"):
        p = p[1:]
    p = p.lstrip(".")
    cur = obj
    for seg in re.split(r"\.|\[(\d+)\]", p):
        if seg is None or seg == "":
            continue
        if seg.isdigit() and isinstance(cur, list):
            cur = cur[int(seg)]
        elif isinstance(cur, dict):
            cur = cur.get(seg)
            if cur is None:
                return None
        else:
            return None
    return cur


async def _fetch_url_value(cfg: dict[str, Any]) -> tuple[float | None, str]:
    url = (cfg.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return None, "url must be http(s)://..."
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Vynaris/0.3 (KR refresh)"})
    except Exception as e:
        return None, f"fetch failed: {e}"
    if r.status_code >= 400:
        return None, f"HTTP {r.status_code}"
    ct = r.headers.get("content-type", "")
    jp = cfg.get("json_path")
    rx = cfg.get("regex")
    if jp or "application/json" in ct:
        try:
            data = r.json()
        except Exception as e:
            return None, f"not JSON: {e}"
        target = _json_path_lookup(data, jp) if jp else data
        v = _to_float(target)
        if v is None:
            return None, f"no number at json_path {jp!r}"
        return v, f"GET {url[:60]}"
    text = r.text
    if rx:
        m = re.search(rx, text)
        if m:
            grp = m.group(1) if m.groups() else m.group(0)
            v = _to_float(grp)
            if v is not None:
                return v, f"GET {url[:60]} (regex)"
        return None, f"regex {rx!r} no match"
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if m:
        return _to_float(m.group(0)), f"GET {url[:60]} (first number)"
    return None, "no numeric value in response"


# ── formula ────────────────────────────────────────────────────────────────

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"min": min, "max": max, "abs": abs, "round": round, "sum": sum}


def _safe_eval(node: ast.AST, names: dict[str, float]) -> Any:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, names)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"constant {node.value!r} not allowed")
    if isinstance(node, ast.Name):
        if node.id in names:
            return names[node.id]
        raise ValueError(f"unknown name: {node.id}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_safe_eval(node.left, names), _safe_eval(node.right, names))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_safe_eval(node.operand, names))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        args = [_safe_eval(a, names) for a in node.args]
        return _FUNCS[node.func.id](*args)
    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval(e, names) for e in node.elts)
    if isinstance(node, ast.List):
        return [_safe_eval(e, names) for e in node.elts]
    raise ValueError(f"expression node {type(node).__name__} not allowed")


async def _eval_formula_value(
    db: AsyncSession, *, kr: KeyResult, cfg: dict[str, Any],
) -> tuple[float | None, str]:
    expr = (cfg.get("expr") or cfg.get("formula") or "").strip()
    if not expr:
        return None, "missing expr"
    siblings = (
        await db.execute(select(KeyResult).where(KeyResult.goal_id == kr.goal_id))
    ).scalars().all()
    names: dict[str, float] = {}
    for s in siblings:
        if s.id == kr.id:
            continue
        alias = ((s.measurement_config or {}).get("alias") or "").strip()
        if alias and s.current_value is not None:
            names[alias] = float(s.current_value)
    try:
        tree = ast.parse(expr, mode="eval")
        val = _safe_eval(tree, names)
    except Exception as e:
        return None, f"formula error: {e}"
    v = _to_float(val)
    if v is None:
        return None, "formula did not return a number"
    return v, f"= {expr} with {names}"


# ── orchestration ──────────────────────────────────────────────────────────

def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).strip().replace(",", "").rstrip("%$"))
    except (TypeError, ValueError):
        return None


async def refresh_kr(
    db: AsyncSession, *, kr: KeyResult, goal: Goal, force: bool = False,
) -> tuple[bool, str]:
    """Refresh a single KR. Returns (changed, message)."""
    if kr.measurement_kind == "manual":
        return False, "manual KR — nothing to refresh"
    if not force and not _is_due(kr):
        return False, "not due"
    cfg = kr.measurement_config or {}
    new_val: float | None = None
    info = ""
    if kr.measurement_kind == "workspace_file":
        new_val, info = _read_workspace_file_value(goal.owner_id, cfg)
    elif kr.measurement_kind == "url":
        new_val, info = await _fetch_url_value(cfg)
    elif kr.measurement_kind == "formula":
        new_val, info = await _eval_formula_value(db, kr=kr, cfg=cfg)
    else:
        return False, f"unknown kind: {kr.measurement_kind}"

    now = datetime.now(timezone.utc)
    if new_val is None:
        kr.last_updated_at = now  # mark attempted so we don't hammer
        return False, info or "no value"

    prev = kr.current_value
    kr.current_value = new_val
    kr.last_updated_at = now
    kr.last_updated_by_id = None
    kr.last_updated_by_agent = True

    if prev is None or abs((prev or 0.0) - new_val) > 1e-9:
        await post_system_event(
            db, channel_id=goal.channel_id, actor_id=None,
            event="kr_value_changed",
            summary=f"{kr.name}: {prev if prev is not None else '—'} → {new_val} {kr.unit}".strip(),
            extra={
                "kr_id": str(kr.id), "from": prev, "to": new_val, "unit": kr.unit,
                "is_agent": True, "source": kr.measurement_kind, "info": info,
            },
        )
        return True, info
    return False, f"no change ({info})"


async def refresh_all_due() -> dict[str, int]:
    """Scan every non-manual KR and refresh those that are due.
    Formulas run after their inputs, so we iterate twice per goal."""
    changed_total = 0
    attempted = 0
    async with AsyncSessionLocal() as db:
        krs = (
            await db.execute(
                select(KeyResult).where(KeyResult.measurement_kind.in_(("workspace_file", "url", "formula")))
            )
        ).scalars().all()
        goals_by_id: dict[uuid.UUID, Goal] = {}
        for kr in krs:
            if kr.goal_id not in goals_by_id:
                g = (await db.execute(select(Goal).where(Goal.id == kr.goal_id))).scalar_one_or_none()
                if g is not None:
                    goals_by_id[kr.goal_id] = g
        # two passes: non-formula first, then formula
        for pass_kinds in (("workspace_file", "url"), ("formula",)):
            for kr in krs:
                if kr.measurement_kind not in pass_kinds:
                    continue
                g = goals_by_id.get(kr.goal_id)
                if g is None or g.state != "open" or g.channel_id is None:
                    continue
                if not _is_due(kr):
                    continue
                attempted += 1
                try:
                    changed, info = await refresh_kr(db, kr=kr, goal=g, force=False)
                    if changed:
                        changed_total += 1
                        log.info("KR %s refreshed: %s", kr.id, info)
                except Exception as e:
                    log.exception("KR %s refresh failed: %s", kr.id, e)
        await db.commit()
    return {"attempted": attempted, "changed": changed_total}
