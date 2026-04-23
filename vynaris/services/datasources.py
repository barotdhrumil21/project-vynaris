"""Org data sources + per-employee scope gates.

A DataSource is a logical data store (an HR database, a sales ledger, a Google
Sheet). The agent reaches it through tools; those tools MUST pass every call
through ``check_scope(person, ds, action)`` before executing. Absence of a
grant means "no access" — there is no org-wide implicit read.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db.models import DataSource, DataSourceGrant, GoalDataSource, Person


# Canonical kinds the UI and seeders reason about. Add new kinds here only
# when a corresponding tool handler exists.
KIND_SQLITE = "sqlite"
KIND_POSTGRES = "postgres"
KIND_GSHEET = "gsheet"
KIND_GDRIVE = "gdrive"
KIND_NOTION = "notion"
KIND_CSV_FILE = "csv_file"
KIND_HTTP_JSON = "http_json"

KIND_LABELS: dict[str, str] = {
    KIND_SQLITE: "SQLite (sample)",
    KIND_POSTGRES: "Postgres",
    KIND_GSHEET: "Google Sheet",
    KIND_GDRIVE: "Google Drive",
    KIND_NOTION: "Notion",
    KIND_CSV_FILE: "CSV file",
    KIND_HTTP_JSON: "HTTP JSON",
}

# Only SQLite has a live tool handler in this build; the rest render as
# "listed" and are seedable for the demo but have no query path yet.
LIVE_KINDS: frozenset[str] = frozenset({KIND_SQLITE})

ACTIONS = ("read", "write", "export", "see_pii")


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:128] or "source"


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def list_for_org(db: AsyncSession, org_id: uuid.UUID) -> list[DataSource]:
    return list(
        (
            await db.execute(
                select(DataSource).where(DataSource.org_id == org_id).order_by(DataSource.name)
            )
        ).scalars().all()
    )


async def get(db: AsyncSession, ds_id: uuid.UUID) -> DataSource | None:
    return (await db.execute(select(DataSource).where(DataSource.id == ds_id))).scalar_one_or_none()


async def get_by_slug(db: AsyncSession, org_id: uuid.UUID, slug: str) -> DataSource | None:
    return (
        await db.execute(
            select(DataSource).where(DataSource.org_id == org_id, DataSource.slug == slug)
        )
    ).scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    name: str,
    kind: str,
    connection: dict[str, Any] | None = None,
    description: str = "",
    pii_columns: dict[str, list[str]] | None = None,
    created_by_id: uuid.UUID | None = None,
) -> DataSource:
    slug = _slug(name)
    existing = await get_by_slug(db, org_id, slug)
    if existing is not None:
        return existing
    ds = DataSource(
        org_id=org_id,
        name=name.strip()[:128],
        slug=slug,
        kind=kind,
        description=description.strip(),
        connection=connection or {},
        pii_columns=pii_columns or {},
        created_by_id=created_by_id,
    )
    db.add(ds)
    await db.flush()
    return ds


# ── Grants ────────────────────────────────────────────────────────────────────


async def grant(
    db: AsyncSession,
    *,
    data_source_id: uuid.UUID,
    person_id: uuid.UUID,
    can_read: bool = True,
    can_write: bool = False,
    can_export: bool = False,
    can_see_pii: bool = False,
    granted_by_id: uuid.UUID | None = None,
) -> DataSourceGrant:
    row = (
        await db.execute(
            select(DataSourceGrant).where(
                DataSourceGrant.data_source_id == data_source_id,
                DataSourceGrant.person_id == person_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = DataSourceGrant(
            data_source_id=data_source_id,
            person_id=person_id,
            granted_by_id=granted_by_id,
        )
        db.add(row)
    row.can_read = bool(can_read)
    row.can_write = bool(can_write)
    row.can_export = bool(can_export)
    row.can_see_pii = bool(can_see_pii)
    if granted_by_id is not None:
        row.granted_by_id = granted_by_id
    await db.flush()
    return row


async def revoke(db: AsyncSession, *, data_source_id: uuid.UUID, person_id: uuid.UUID) -> None:
    row = (
        await db.execute(
            select(DataSourceGrant).where(
                DataSourceGrant.data_source_id == data_source_id,
                DataSourceGrant.person_id == person_id,
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.flush()


async def get_grant(
    db: AsyncSession, *, data_source_id: uuid.UUID, person_id: uuid.UUID,
) -> DataSourceGrant | None:
    return (
        await db.execute(
            select(DataSourceGrant).where(
                DataSourceGrant.data_source_id == data_source_id,
                DataSourceGrant.person_id == person_id,
            )
        )
    ).scalar_one_or_none()


async def grants_for_person(db: AsyncSession, person_id: uuid.UUID) -> list[DataSourceGrant]:
    return list(
        (
            await db.execute(
                select(DataSourceGrant).where(DataSourceGrant.person_id == person_id)
            )
        ).scalars().all()
    )


async def grants_for_source(db: AsyncSession, data_source_id: uuid.UUID) -> list[DataSourceGrant]:
    return list(
        (
            await db.execute(
                select(DataSourceGrant).where(DataSourceGrant.data_source_id == data_source_id)
            )
        ).scalars().all()
    )


# ── Scope gate ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScopeDecision:
    ok: bool
    reason: str = ""


async def check_scope(
    db: AsyncSession,
    *,
    person: Person,
    data_source: DataSource,
    action: str,
    columns: list[str] | None = None,
) -> ScopeDecision:
    """Authoritative yes/no for an agent-initiated data action.

    ``action`` is one of: read | write | export | see_pii.
    ``columns`` is optional; if any column in it is PII-tagged, the caller
    also needs ``see_pii``. The check returns deny on the first fail.
    """
    if person.org_id != data_source.org_id:
        return ScopeDecision(False, "data source is not in your org")
    if action not in ACTIONS:
        return ScopeDecision(False, f"unknown action: {action}")
    grant_row = await get_grant(
        db, data_source_id=data_source.id, person_id=person.id,
    )
    if grant_row is None:
        return ScopeDecision(False, "no grant — this data source is not enabled for you")
    flag = {
        "read": grant_row.can_read,
        "write": grant_row.can_write,
        "export": grant_row.can_export,
        "see_pii": grant_row.can_see_pii,
    }[action]
    if not flag:
        return ScopeDecision(False, f"your grant does not permit: {action}")
    if columns:
        pii_map = data_source.pii_columns or {}
        pii_cols = {c.lower() for cols in pii_map.values() for c in cols}
        hits = [c for c in columns if c.lower() in pii_cols]
        if hits and not grant_row.can_see_pii:
            return ScopeDecision(False, f"PII columns require see_pii grant: {', '.join(hits)}")
    return ScopeDecision(True, "")


# ── Goal ↔ data source links ─────────────────────────────────────────────────


async def attach_to_goal(
    db: AsyncSession, *, goal_id: uuid.UUID, data_source_id: uuid.UUID,
) -> GoalDataSource:
    existing = (
        await db.execute(
            select(GoalDataSource).where(
                GoalDataSource.goal_id == goal_id,
                GoalDataSource.data_source_id == data_source_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    row = GoalDataSource(goal_id=goal_id, data_source_id=data_source_id)
    db.add(row)
    await db.flush()
    return row


async def detach_from_goal(
    db: AsyncSession, *, goal_id: uuid.UUID, data_source_id: uuid.UUID,
) -> None:
    row = (
        await db.execute(
            select(GoalDataSource).where(
                GoalDataSource.goal_id == goal_id,
                GoalDataSource.data_source_id == data_source_id,
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.flush()


async def sources_for_goal(db: AsyncSession, goal_id: uuid.UUID) -> list[DataSource]:
    links = (
        await db.execute(
            select(GoalDataSource).where(GoalDataSource.goal_id == goal_id)
        )
    ).scalars().all()
    ids = [link.data_source_id for link in links]
    if not ids:
        return []
    return list(
        (
            await db.execute(select(DataSource).where(DataSource.id.in_(ids)).order_by(DataSource.name))
        ).scalars().all()
    )


async def sources_for_person(db: AsyncSession, person_id: uuid.UUID) -> list[tuple[DataSource, DataSourceGrant]]:
    """Every data source the person has a grant on, paired with the grant."""
    grants = await grants_for_person(db, person_id)
    if not grants:
        return []
    ds_by_id = {
        ds.id: ds
        for ds in (
            await db.execute(
                select(DataSource).where(DataSource.id.in_([g.data_source_id for g in grants]))
            )
        ).scalars().all()
    }
    out: list[tuple[DataSource, DataSourceGrant]] = []
    for g in grants:
        ds = ds_by_id.get(g.data_source_id)
        if ds is not None:
            out.append((ds, g))
    out.sort(key=lambda p: p[0].name)
    return out
