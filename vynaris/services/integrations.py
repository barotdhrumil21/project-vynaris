"""Integrations service — encrypted credential store + catalog.

The CATALOG is the full list of integrations the UI advertises. Only a few
are actually wired to live tools; the rest render as "coming soon". Each
Integration row in the DB has `status` = connected | disconnected | coming_soon.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from vynaris.config import get_settings
from vynaris.db.models import Integration
from vynaris.db.session import AsyncSessionLocal

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntegrationSpec:
    kind: str
    display_name: str
    icon: str
    category: str             # "productivity", "data", "social", "dev", ...
    tagline: str
    implemented: bool = False  # False → UI shows "coming soon"


CATALOG: list[IntegrationSpec] = [
    IntegrationSpec("gmail", "Gmail", "✉️", "productivity",
                    "Read and send email on your behalf.", implemented=True),
    IntegrationSpec("gsheets", "Google Sheets", "📊", "data",
                    "Read KPI spreadsheets."),
    IntegrationSpec("excel", "Excel", "📗", "data",
                    "Read workbooks and KPI sheets."),
    IntegrationSpec("x", "X (Twitter)", "𝕏", "social",
                    "Search posts and monitor mentions."),
    IntegrationSpec("postgres", "Postgres", "🐘", "data",
                    "Run read-only queries against your database."),
    IntegrationSpec("webhook", "Generic webhook", "🪝", "dev",
                    "Call arbitrary HTTP endpoints."),
    IntegrationSpec("stripe", "Stripe", "💳", "data",
                    "Revenue metrics + customer lookup."),
    IntegrationSpec("hubspot", "HubSpot", "🔶", "productivity",
                    "CRM sync and contact lookup."),
    IntegrationSpec("salesforce", "Salesforce", "☁️", "productivity",
                    "Opportunity + account data."),
    IntegrationSpec("notion", "Notion", "📝", "productivity",
                    "Read and update pages."),
    IntegrationSpec("linear", "Linear", "📐", "dev",
                    "Issue tracking and project sync."),
    IntegrationSpec("github", "GitHub", "🐙", "dev",
                    "PR + issue activity for engineering goals."),
]


def _fernet() -> Fernet:
    s = get_settings()
    raw = s.integration_encryption_key.strip() or s.vynaris_secret_key
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_config(data: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(data).encode("utf-8")).decode("utf-8")


def decrypt_config(blob: str) -> dict[str, Any]:
    if not blob:
        return {}
    try:
        raw = _fernet().decrypt(blob.encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except (InvalidToken, ValueError):
        log.warning("integration config failed to decrypt — resetting")
        return {}


async def ensure_catalog(org_id: uuid.UUID) -> None:
    """Seed the Integration table with one row per CATALOG entry for this org.
    Implemented integrations start as 'disconnected'; others as 'coming_soon'."""
    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(select(Integration).where(Integration.org_id == org_id))
        ).scalars().all()
        by_kind = {r.kind: r for r in rows}
        for spec in CATALOG:
            r = by_kind.get(spec.kind)
            status = "coming_soon" if not spec.implemented else "disconnected"
            if r is None:
                s.add(Integration(
                    org_id=org_id, kind=spec.kind,
                    display_name=spec.display_name,
                    status=status,
                ))
            else:
                r.display_name = spec.display_name
                if not spec.implemented and r.status != "connected":
                    r.status = "coming_soon"
        await s.commit()


async def list_for_org(org_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return integrations joined with CATALOG metadata for UI rendering."""
    await ensure_catalog(org_id)
    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(select(Integration).where(Integration.org_id == org_id))
        ).scalars().all()
    by_kind = {r.kind: r for r in rows}
    out: list[dict[str, Any]] = []
    for spec in CATALOG:
        r = by_kind.get(spec.kind)
        out.append({
            "spec": spec,
            "row": r,
            "status": r.status if r else ("disconnected" if spec.implemented else "coming_soon"),
            "connected_at": r.connected_at if r else None,
        })
    return out


async def get(org_id: uuid.UUID, kind: str) -> Integration | None:
    async with AsyncSessionLocal() as s:
        return (
            await s.execute(
                select(Integration).where(Integration.org_id == org_id, Integration.kind == kind)
            )
        ).scalar_one_or_none()


async def set_connected(
    *, org_id: uuid.UUID, kind: str, config: dict[str, Any], connected_by_id: uuid.UUID,
) -> Integration:
    async with AsyncSessionLocal() as s:
        row = (
            await s.execute(
                select(Integration).where(Integration.org_id == org_id, Integration.kind == kind)
            )
        ).scalar_one_or_none()
        if row is None:
            row = Integration(org_id=org_id, kind=kind)
            s.add(row)
        row.config_encrypted = encrypt_config(config)
        row.status = "connected"
        row.connected_at = datetime.now(timezone.utc)
        row.connected_by_id = connected_by_id
        await s.commit()
        await s.refresh(row)
        return row


async def disconnect(org_id: uuid.UUID, kind: str) -> None:
    async with AsyncSessionLocal() as s:
        row = (
            await s.execute(
                select(Integration).where(Integration.org_id == org_id, Integration.kind == kind)
            )
        ).scalar_one_or_none()
        if row is None:
            return
        row.config_encrypted = ""
        row.status = "disconnected"
        row.connected_at = None
        row.connected_by_id = None
        await s.commit()
