"""Departments — org subdivision used for goal ownership and team rollup."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db.models import Department, Person


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:128] or "dept"


async def list_for_org(db: AsyncSession, org_id: uuid.UUID) -> list[Department]:
    return list(
        (
            await db.execute(
                select(Department).where(Department.org_id == org_id).order_by(Department.name)
            )
        ).scalars().all()
    )


async def get_by_slug(db: AsyncSession, org_id: uuid.UUID, slug: str) -> Department | None:
    return (
        await db.execute(
            select(Department).where(Department.org_id == org_id, Department.slug == slug)
        )
    ).scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    name: str,
    description: str = "",
    parent_id: uuid.UUID | None = None,
    lead_id: uuid.UUID | None = None,
) -> Department:
    slug = _slug(name)
    existing = await get_by_slug(db, org_id, slug)
    if existing is not None:
        return existing
    dept = Department(
        org_id=org_id,
        name=name.strip()[:128],
        slug=slug,
        description=description.strip(),
        parent_id=parent_id,
        lead_id=lead_id,
    )
    db.add(dept)
    await db.flush()
    return dept


async def members(db: AsyncSession, department_id: uuid.UUID) -> list[Person]:
    return list(
        (
            await db.execute(
                select(Person)
                .where(Person.department_id == department_id)
                .order_by(Person.level, Person.name)
            )
        ).scalars().all()
    )


async def assign(db: AsyncSession, *, person: Person, department_id: uuid.UUID | None) -> None:
    person.department_id = department_id
    await db.flush()
