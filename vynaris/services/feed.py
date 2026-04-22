from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db.models import FeedEntry


async def emit(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID,
    kind: str,
    title: str,
    body: str = "",
    goal_id: uuid.UUID | None = None,
    visibility: str = "team",
    extra: dict[str, Any] | None = None,
) -> FeedEntry:
    entry = FeedEntry(
        org_id=org_id,
        actor_id=actor_id,
        kind=kind,
        title=title,
        body=body,
        goal_id=goal_id,
        visibility=visibility,
        extra=extra or {},
    )
    db.add(entry)
    await db.flush()
    return entry
