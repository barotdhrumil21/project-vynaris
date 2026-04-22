from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db import get_db
from vynaris.db.models import AgentAction, Channel, Goal, Message, Person
from vynaris.services import gates
from vynaris.services.channels import can_view_channel
from vynaris.web.deps import current_person
from vynaris.web.routes.channels import _build_sidebar
from vynaris.web.templating import render

router = APIRouter()


@router.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)

    # pending gated actions — scoped to what viewer can review
    pending_rows = (
        await db.execute(
            select(AgentAction)
            .where(AgentAction.org_id == viewer.org_id, AgentAction.status == "pending")
            .order_by(desc(AgentAction.created_at))
        )
    ).scalars().all()
    pending = [a for a in pending_rows if await gates.can_review(db, viewer, a)]

    # audit log — last 200 system events from channels viewer can see
    since = datetime.now(timezone.utc) - timedelta(days=14)
    events_raw = (
        await db.execute(
            select(Message)
            .where(
                Message.kind == "system_event",
                Message.created_at >= since,
            )
            .order_by(desc(Message.created_at))
            .limit(500)
        )
    ).scalars().all()
    channel_cache: dict[uuid.UUID, Channel | None] = {}
    events: list[Message] = []
    for m in events_raw:
        ch = channel_cache.get(m.channel_id)
        if ch is None and m.channel_id not in channel_cache:
            ch = (await db.execute(select(Channel).where(Channel.id == m.channel_id))).scalar_one_or_none()
            channel_cache[m.channel_id] = ch
        if ch is None:
            continue
        if ch.org_id != viewer.org_id:
            continue
        if not await can_view_channel(db, viewer, ch):
            continue
        events.append(m)
        if len(events) >= 200:
            break

    # aux maps for rendering
    people_by_id = {
        p.id: p
        for p in (await db.execute(select(Person).where(Person.org_id == viewer.org_id))).scalars().all()
    }
    goal_ids = {a.goal_id for a in pending_rows if a.goal_id is not None}
    goals_by_id: dict[uuid.UUID, Goal] = {}
    if goal_ids:
        goals_by_id = {
            g.id: g
            for g in (await db.execute(select(Goal).where(Goal.id.in_(goal_ids)))).scalars().all()
        }

    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "audit.html",
        viewer=viewer, pending=pending, events=events,
        people_by_id=people_by_id, goals_by_id=goals_by_id,
        channel_cache=channel_cache, sidebar=sidebar,
    )


@router.post("/audit/actions/{action_id}/approve")
async def approve_action(
    action_id: uuid.UUID, request: Request,
    note: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    action = await gates.approve(db, action_id, viewer, note=note)
    await db.commit()
    if action is None:
        return RedirectResponse("/audit?err=not_allowed", status_code=303)
    return RedirectResponse("/audit?ok=approved", status_code=303)


@router.post("/audit/actions/{action_id}/deny")
async def deny_action(
    action_id: uuid.UUID, request: Request,
    note: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    action = await gates.deny(db, action_id, viewer, note=note)
    await db.commit()
    if action is None:
        return RedirectResponse("/audit?err=not_allowed", status_code=303)
    return RedirectResponse("/audit?ok=denied", status_code=303)
