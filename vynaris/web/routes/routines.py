"""Routines view = scheduled skills.

Routines are not a DB entity. They are Claude Agent SDK skills whose frontmatter
carries ``schedule:`` / ``scope:`` / ``fires_only_when:``. This view lets an org
see every scheduled skill, run one on-demand, toggle it for the org, and
override the cadence without editing the markdown.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.agent.skill_loader import find_skill, load_platform_skills
from vynaris.db import get_db
from vynaris.db.models import AgentRun, Person, ScheduledSkillOverride
from vynaris.services import scheduled_skills as ssvc
from vynaris.services.scheduler import on_schedule_changed
from vynaris.web.deps import current_person, require_admin
from vynaris.web.routes.channels import _build_sidebar
from vynaris.web.templating import render

router = APIRouter()


@router.get("/routines", response_class=HTMLResponse)
async def routines_list(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    schedules = await ssvc.effective_schedules_for_org(db, viewer.org_id)
    # also list every platform skill (including non-scheduled) for visibility
    all_skills = load_platform_skills()
    scheduled_names = {s.skill.name for s in schedules}
    ad_hoc_skills = [s for s in all_skills if s.name not in scheduled_names]
    sidebar = await _build_sidebar(db, viewer)
    flash = {"ok": request.query_params.get("ok"), "err": request.query_params.get("err")}
    return render(
        request, "routines.html",
        viewer=viewer, schedules=schedules, ad_hoc_skills=ad_hoc_skills,
        sidebar=sidebar, flash=flash,
    )


@router.get("/routines/{skill_name}", response_class=HTMLResponse)
async def routine_detail(skill_name: str, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    skill = find_skill(skill_name)
    if skill is None:
        return RedirectResponse("/routines", status_code=303)
    effective_list = await ssvc.effective_schedules_for_org(db, viewer.org_id)
    effective = next((e for e in effective_list if e.skill.name == skill_name), None)
    override = (
        await db.execute(
            select(ScheduledSkillOverride).where(
                ScheduledSkillOverride.org_id == viewer.org_id,
                ScheduledSkillOverride.skill_name == skill_name,
            )
        )
    ).scalar_one_or_none()
    runs = await ssvc.recent_runs_for_skill(db, skill_name, viewer.org_id, limit=50)
    people_by_id = {
        p.id: p
        for p in (await db.execute(select(Person).where(Person.org_id == viewer.org_id))).scalars().all()
    }
    sidebar = await _build_sidebar(db, viewer)
    flash = {
        "ok": request.query_params.get("ok"),
        "err": request.query_params.get("err"),
        "fired": request.query_params.get("fired"),
    }
    return render(
        request, "routine_detail.html",
        viewer=viewer, skill=skill, effective=effective, override=override,
        runs=runs, people_by_id=people_by_id, sidebar=sidebar, flash=flash,
        body_preview=skill.body(),
    )


@router.post("/routines/{skill_name}/toggle")
async def routine_toggle(skill_name: str, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await require_admin(request, db)
    if find_skill(skill_name) is None:
        return RedirectResponse("/routines?err=not_found", status_code=303)
    await ssvc.toggle_override(db, org_id=viewer.org_id, skill_name=skill_name)
    await db.commit()
    await on_schedule_changed(viewer.org_id, skill_name)
    return RedirectResponse(f"/routines/{skill_name}?ok=toggled", status_code=303)


@router.post("/routines/{skill_name}/schedule")
async def routine_set_schedule(
    skill_name: str, request: Request,
    schedule_cron: str = Form(""),
    schedule_interval_minutes: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    if find_skill(skill_name) is None:
        return RedirectResponse("/routines?err=not_found", status_code=303)
    interval: int | None
    try:
        interval = int(schedule_interval_minutes) if schedule_interval_minutes.strip() else None
    except ValueError:
        interval = None
    await ssvc.set_schedule_override(
        db, org_id=viewer.org_id, skill_name=skill_name,
        cron=schedule_cron, interval_minutes=interval,
    )
    await db.commit()
    await on_schedule_changed(viewer.org_id, skill_name)
    return RedirectResponse(f"/routines/{skill_name}?ok=rescheduled", status_code=303)


@router.post("/routines/{skill_name}/run")
async def routine_run_now(skill_name: str, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    skill = find_skill(skill_name)
    if skill is None:
        return RedirectResponse("/routines?err=not_found", status_code=303)
    stats = await ssvc.fire_skill(skill_name, org_id=viewer.org_id)
    return RedirectResponse(
        f"/routines/{skill_name}?ok=ran&fired={stats.get('fired', 0)}", status_code=303,
    )
