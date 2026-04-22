"""Data-source visibility: org-wide inventory + per-goal detail."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db import get_db
from vynaris.db.models import Goal, KeyResult, Person
from vynaris.services.data_sources import (
    kr_freshness, kr_source_preview, kr_value_history, sparkline_svg,
)
from vynaris.services.visibility import can_view_goal
from vynaris.web.deps import current_person
from vynaris.web.routes.channels import _build_sidebar
from vynaris.web.templating import render

router = APIRouter()


@router.get("/data", response_class=HTMLResponse)
async def data_inventory(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)

    goals = (
        await db.execute(
            select(Goal)
            .where(Goal.org_id == viewer.org_id, Goal.state == "open")
            .order_by(Goal.created_at)
        )
    ).scalars().all()
    visible_goals = [g for g in goals if await can_view_goal(db, viewer, g)]

    krs = []
    if visible_goals:
        krs = list(
            (
                await db.execute(
                    select(KeyResult)
                    .where(
                        KeyResult.goal_id.in_([g.id for g in visible_goals]),
                        KeyResult.measurement_kind != "manual",
                    )
                    .order_by(KeyResult.goal_id, KeyResult.sort)
                )
            ).scalars().all()
        )
    goals_by_id = {g.id: g for g in visible_goals}

    rows = []
    totals = {"fresh": 0, "stale": 0, "never": 0}
    for kr in krs:
        g = goals_by_id.get(kr.goal_id)
        if g is None:
            continue
        f = kr_freshness(kr)
        if f.status in totals:
            totals[f.status] += 1
        rows.append({"kr": kr, "goal": g, "freshness": f})

    people_by_id = {
        p.id: p
        for p in (await db.execute(select(Person).where(Person.org_id == viewer.org_id))).scalars().all()
    }
    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "data_inventory.html",
        viewer=viewer, rows=rows, totals=totals,
        people_by_id=people_by_id, sidebar=sidebar,
    )


@router.get("/g/{goal_id}/data", response_class=HTMLResponse)
async def goal_data_panel(goal_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    goal = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if goal is None or goal.org_id != viewer.org_id:
        return RedirectResponse("/goals", status_code=303)
    if not await can_view_goal(db, viewer, goal):
        return RedirectResponse("/goals", status_code=303)

    krs = list(
        (
            await db.execute(
                select(KeyResult).where(KeyResult.goal_id == goal.id).order_by(KeyResult.sort)
            )
        ).scalars().all()
    )

    panels = []
    for kr in krs:
        history = await kr_value_history(db, kr_id=kr.id, goal=goal, limit=24)
        preview = kr_source_preview(kr, goal)
        fresh = kr_freshness(kr)
        spark = sparkline_svg(history) if len(history) >= 2 else ""
        panels.append({
            "kr": kr,
            "history": history,
            "preview": preview,
            "freshness": fresh,
            "sparkline": spark,
        })

    owner = (await db.execute(select(Person).where(Person.id == goal.owner_id))).scalar_one_or_none()
    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "goal_data.html",
        viewer=viewer, goal=goal, owner=owner, panels=panels, sidebar=sidebar,
    )
