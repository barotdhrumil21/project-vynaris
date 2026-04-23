"""External-link flow: generate short code → user DMs bot /link CODE → verify + bind."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from vynaris.db.models import Channel, ExternalLink, Org, Person
from vynaris.db.session import AsyncSessionLocal

LINK_CODE_TTL = timedelta(minutes=15)


@dataclass
class Binding:
    person_id: uuid.UUID
    org_id: uuid.UUID
    channel_id: uuid.UUID


@dataclass
class VerifyResult:
    ok: bool
    person_name: str = ""
    org_name: str = ""
    error: str = ""


def _new_code() -> str:
    return secrets.token_urlsafe(5).replace("_", "").replace("-", "").upper()[:8] or secrets.token_hex(3).upper()


async def generate_link_code(*, person_id: uuid.UUID, platform: str) -> str:
    """Create (or refresh) a pending ExternalLink row and return its code."""
    async with AsyncSessionLocal() as s:
        person = (await s.execute(select(Person).where(Person.id == person_id))).scalar_one()
        existing = (
            await s.execute(
                select(ExternalLink).where(
                    ExternalLink.person_id == person.id,
                    ExternalLink.platform == platform,
                    ExternalLink.verified_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        code = _new_code()
        expires = datetime.now(timezone.utc) + LINK_CODE_TTL
        if existing is None:
            s.add(ExternalLink(
                org_id=person.org_id, person_id=person.id, platform=platform,
                link_code=code, link_code_expires_at=expires,
            ))
        else:
            existing.link_code = code
            existing.link_code_expires_at = expires
        await s.commit()
    return code


async def verify_link_code(
    *, platform: str, code: str, external_user_id: str, external_handle: str,
) -> VerifyResult:
    code = (code or "").strip().upper()
    if not code:
        return VerifyResult(ok=False, error="empty code")
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as s:
        row = (
            await s.execute(
                select(ExternalLink).where(
                    ExternalLink.platform == platform,
                    ExternalLink.link_code == code,
                    ExternalLink.verified_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return VerifyResult(ok=False, error="unknown code")
        if row.link_code_expires_at is not None and row.link_code_expires_at < now:
            return VerifyResult(ok=False, error="code expired — generate a new one")

        person = (await s.execute(select(Person).where(Person.id == row.person_id))).scalar_one()
        org = (await s.execute(select(Org).where(Org.id == person.org_id))).scalar_one()

        channel = (
            await s.execute(
                select(Channel).where(
                    Channel.agent_for_id == person.id,
                    Channel.external_platform == platform,
                    Channel.external_user_id == external_user_id,
                )
            )
        ).scalar_one_or_none()
        if channel is None:
            channel = Channel(
                org_id=person.org_id,
                name=f"{platform}:{external_handle or external_user_id}",
                slug=f"{platform}-{external_user_id}",
                kind=platform,
                external_platform=platform,
                external_user_id=external_user_id,
                external_meta={"handle": external_handle},
                agent_for_id=person.id,
                created_by_id=person.id,
            )
            s.add(channel)
            await s.flush()

        row.external_user_id = external_user_id
        row.external_handle = external_handle
        row.verified_at = now
        row.link_code = ""
        row.link_code_expires_at = None
        row.channel_id = channel.id
        await s.commit()
        return VerifyResult(ok=True, person_name=person.name, org_name=org.name)


async def lookup_binding(*, platform: str, external_user_id: str) -> Binding | None:
    async with AsyncSessionLocal() as s:
        row = (
            await s.execute(
                select(ExternalLink).where(
                    ExternalLink.platform == platform,
                    ExternalLink.external_user_id == external_user_id,
                    ExternalLink.verified_at.isnot(None),
                )
            )
        ).scalar_one_or_none()
        if row is None or row.channel_id is None:
            return None
        return Binding(person_id=row.person_id, org_id=row.org_id, channel_id=row.channel_id)


async def list_links_for_person(person_id: uuid.UUID) -> list[ExternalLink]:
    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(
                select(ExternalLink).where(ExternalLink.person_id == person_id)
            )
        ).scalars().all()
    return list(rows)


async def unlink(*, person_id: uuid.UUID, platform: str) -> None:
    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(
                select(ExternalLink).where(
                    ExternalLink.person_id == person_id,
                    ExternalLink.platform == platform,
                )
            )
        ).scalars().all()
        for r in rows:
            await s.delete(r)
        await s.commit()
