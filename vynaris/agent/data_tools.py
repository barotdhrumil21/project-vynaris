"""Data-source tools for the agent — scope-gated per DataSourceGrant.

Every tool call routes through ``datasources.check_scope(person, ds, action)``.
Absence of a grant ⇒ hard deny. SQLite is the only live kind in this build.
"""

from __future__ import annotations

import asyncio
import csv
import io
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from claude_agent_sdk import tool

from vynaris.db.models import DataSource, Person
from vynaris.db.session import AsyncSessionLocal
from vynaris.services import datasources as ds_svc
from vynaris.services.workspace import workspace_root


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _err(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Error: {msg}"}], "isError": True}


# ── SQLite helpers (sync, call via asyncio.to_thread) ─────────────────────────


def _open_sqlite_ro(path: str) -> sqlite3.Connection:
    uri = f"file:{Path(path).resolve()}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def _sqlite_describe(path: str) -> str:
    conn = _open_sqlite_ro(path)
    try:
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall() if not r[0].startswith("sqlite_")]
        lines: list[str] = []
        for t in tables:
            info = cur.execute(f"PRAGMA table_info('{t}')").fetchall()
            cols = ", ".join(f"{row[1]}:{row[2]}" for row in info)
            count = cur.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
            lines.append(f"  {t}  ({count} rows)  — {cols}")
        return "\n".join(lines) or "(no tables)"
    finally:
        conn.close()


def _sqlite_select(path: str, sql: str, limit: int) -> tuple[list[str], list[tuple]]:
    conn = _open_sqlite_ro(path)
    try:
        cur = conn.cursor()
        if not re.search(r"\blimit\b", sql, re.IGNORECASE):
            sql = f"{sql.rstrip(';').strip()} LIMIT {int(limit)}"
        cur.execute(sql)
        cols = [d[0] for d in (cur.description or [])]
        rows = cur.fetchall()
        return cols, rows
    finally:
        conn.close()


def _format_table(cols: list[str], rows: list[tuple], max_rows: int = 50) -> str:
    if not cols:
        return "(no columns)"
    head = " | ".join(cols)
    sep = " | ".join("-" * max(3, len(c)) for c in cols)
    body_rows = rows[:max_rows]
    body = "\n".join(" | ".join(_cell(v) for v in row) for row in body_rows)
    suffix = "" if len(rows) <= max_rows else f"\n... ({len(rows) - max_rows} more rows)"
    return f"{head}\n{sep}\n{body}{suffix}"


def _cell(v: Any) -> str:
    if v is None:
        return "NULL"
    s = str(v)
    return s if len(s) <= 80 else s[:77] + "..."


# ── PII / write detection (naive; strong enough for demo) ─────────────────────


_WRITE_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|create|alter|replace|truncate|attach|detach)\b",
    re.IGNORECASE,
)


def _looks_like_write(sql: str) -> bool:
    return bool(_WRITE_KEYWORDS.search(sql or ""))


def _pii_hits(sql: str, pii_columns: dict[str, Any]) -> list[str]:
    if not pii_columns:
        return []
    tokens = {t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", sql or "")}
    hits: list[str] = []
    for cols in pii_columns.values():
        for col in cols:
            c = str(col).lower()
            if c in tokens:
                hits.append(col)
    # SELECT * implies every column including PII ones
    if re.search(r"select\s+\*", sql or "", re.IGNORECASE):
        for cols in pii_columns.values():
            for col in cols:
                if col not in hits:
                    hits.append(col)
    return hits


# ── Tool builders ─────────────────────────────────────────────────────────────


async def _load_person_and_ds(
    person_id: uuid.UUID, ds_id_raw: str,
) -> tuple[Person, DataSource] | tuple[None, str]:
    try:
        ds_id = uuid.UUID(str(ds_id_raw))
    except (TypeError, ValueError):
        return None, "invalid source_id"
    async with AsyncSessionLocal() as s:
        person = (await s.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
        if person is None:
            return None, "person not found"
        ds = (await s.execute(select(DataSource).where(DataSource.id == ds_id))).scalar_one_or_none()
        if ds is None or ds.org_id != person.org_id:
            return None, "data source not found in your org"
    return person, ds


def build_data_tools(
    *, person_id: uuid.UUID, org_id: uuid.UUID,
) -> tuple[list[Any], list[str]]:
    """Return (tools, tool_names). Always registered; each call scope-checks."""

    root = workspace_root(person_id)

    @tool("ds_list",
          "List the data sources enabled for you, with your scopes.", {})
    async def ds_list(args: dict[str, Any]) -> dict[str, Any]:
        async with AsyncSessionLocal() as s:
            pairs = await ds_svc.sources_for_person(s, person_id)
        if not pairs:
            return _ok("(no data sources enabled for you)")
        lines = ["Data sources you can query:"]
        for ds, g in pairs:
            scopes = [name for name, flag in (
                ("read", g.can_read), ("write", g.can_write),
                ("export", g.can_export), ("see_pii", g.can_see_pii),
            ) if flag]
            lines.append(
                f"- {ds.name}  [id={ds.id}]  kind={ds.kind}  scopes={','.join(scopes) or 'none'}"
            )
            if ds.description:
                lines.append(f"    {ds.description}")
        return _ok("\n".join(lines))

    @tool("ds_describe",
          "Show the tables and columns of a data source you can read.",
          {"source_id": str})
    async def ds_describe(args: dict[str, Any]) -> dict[str, Any]:
        loaded = await _load_person_and_ds(person_id, str(args.get("source_id", "")))
        if loaded[0] is None:
            return _err(loaded[1])  # type: ignore[arg-type]
        person, ds = loaded
        async with AsyncSessionLocal() as s:
            decision = await ds_svc.check_scope(s, person=person, data_source=ds, action="read")
        if not decision.ok:
            return _err(decision.reason)
        if ds.kind != ds_svc.KIND_SQLITE:
            return _err(f"describe not supported for kind={ds.kind}")
        path = str((ds.connection or {}).get("path") or "")
        if not path or not Path(path).exists():
            return _err(f"source file missing: {path}")
        try:
            out = await asyncio.to_thread(_sqlite_describe, path)
        except Exception as e:
            return _err(f"describe failed: {e}")
        pii_note = ""
        if ds.pii_columns:
            pii_flat = sorted({c for cols in ds.pii_columns.values() for c in cols})
            pii_note = f"\n\nPII columns on this source: {', '.join(pii_flat)}. Queries touching these need see_pii."
        return _ok(f"Schema for {ds.name}:\n{out}{pii_note}")

    @tool("ds_query",
          "Run a read-only SQL query against a data source. SELECT only. "
          "Every call is scope-checked (read / see_pii) against your grant.",
          {"source_id": str, "sql": str, "limit": int})
    async def ds_query(args: dict[str, Any]) -> dict[str, Any]:
        sql = str(args.get("sql", "")).strip()
        if not sql:
            return _err("sql is required")
        limit = min(max(int(args.get("limit", 50) or 50), 1), 500)
        loaded = await _load_person_and_ds(person_id, str(args.get("source_id", "")))
        if loaded[0] is None:
            return _err(loaded[1])  # type: ignore[arg-type]
        person, ds = loaded
        if _looks_like_write(sql):
            async with AsyncSessionLocal() as s:
                decision = await ds_svc.check_scope(s, person=person, data_source=ds, action="write")
            return _err("this looks like a write/DDL statement — denied. " + decision.reason)
        hits = _pii_hits(sql, ds.pii_columns or {})
        async with AsyncSessionLocal() as s:
            decision = await ds_svc.check_scope(
                s, person=person, data_source=ds, action="read", columns=hits,
            )
        if not decision.ok:
            return _err(decision.reason)
        if ds.kind != ds_svc.KIND_SQLITE:
            return _err(f"query not supported for kind={ds.kind}")
        path = str((ds.connection or {}).get("path") or "")
        if not path or not Path(path).exists():
            return _err(f"source file missing: {path}")
        try:
            cols, rows = await asyncio.to_thread(_sqlite_select, path, sql, limit)
        except sqlite3.OperationalError as e:
            return _err(f"sql error: {e}")
        except Exception as e:
            return _err(f"query failed: {e}")
        return _ok(_format_table(cols, rows))

    @tool("ds_export",
          "Export a SELECT result to a CSV file in your private workspace. "
          "Requires the `export` scope on your grant.",
          {"source_id": str, "sql": str, "filename": str})
    async def ds_export(args: dict[str, Any]) -> dict[str, Any]:
        sql = str(args.get("sql", "")).strip()
        filename = str(args.get("filename", "")).strip() or f"export-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"
        if not filename.endswith(".csv"):
            filename = filename + ".csv"
        if not sql:
            return _err("sql is required")
        if _looks_like_write(sql):
            return _err("export only runs SELECTs")
        loaded = await _load_person_and_ds(person_id, str(args.get("source_id", "")))
        if loaded[0] is None:
            return _err(loaded[1])  # type: ignore[arg-type]
        person, ds = loaded
        hits = _pii_hits(sql, ds.pii_columns or {})
        async with AsyncSessionLocal() as s:
            read_ok = await ds_svc.check_scope(
                s, person=person, data_source=ds, action="read", columns=hits,
            )
            if not read_ok.ok:
                return _err(read_ok.reason)
            exp_ok = await ds_svc.check_scope(s, person=person, data_source=ds, action="export")
            if not exp_ok.ok:
                return _err(exp_ok.reason)
        if ds.kind != ds_svc.KIND_SQLITE:
            return _err(f"export not supported for kind={ds.kind}")
        path = str((ds.connection or {}).get("path") or "")
        if not path or not Path(path).exists():
            return _err(f"source file missing: {path}")
        try:
            cols, rows = await asyncio.to_thread(_sqlite_select, path, sql, 10_000)
        except sqlite3.OperationalError as e:
            return _err(f"sql error: {e}")
        except Exception as e:
            return _err(f"query failed: {e}")
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        for row in rows:
            w.writerow(row)
        out_path = root / "private" / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(buf.getvalue(), encoding="utf-8")
        return _ok(f"exported {len(rows)} rows → private/{filename}")

    tools = [ds_list, ds_describe, ds_query, ds_export]
    names = [
        "mcp__vynaris__ds_list",
        "mcp__vynaris__ds_describe",
        "mcp__vynaris__ds_query",
        "mcp__vynaris__ds_export",
    ]
    return tools, names
