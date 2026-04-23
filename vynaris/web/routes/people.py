from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.auth import new_invite_token
from vynaris.db import get_db
from vynaris.db.models import Org, Person
from vynaris.services.onboarding import PersonDraft, bulk_import_people, create_person
from vynaris.web.deps import current_person, require_admin
from vynaris.web.templating import render

router = APIRouter()


@router.get("/people", response_class=HTMLResponse)
async def people_list(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    org = (await db.execute(select(Org).where(Org.id == viewer.org_id))).scalar_one()
    people = (
        await db.execute(
            select(Person)
            .where(Person.org_id == org.id)
            .order_by(Person.is_admin.desc(), Person.level.asc(), Person.name)
        )
    ).scalars().all()
    people_by_id = {p.id: p for p in people}
    from vynaris.services import departments as dept_svc
    depts = await dept_svc.list_for_org(db, org.id)
    dept_by_id = {d.id: d for d in depts}
    sidebar = await _sidebar(db, viewer)
    base_url = str(request.base_url).rstrip("/")
    flash = {
        "imported": request.query_params.get("imported"),
        "skipped": request.query_params.get("skipped"),
        "errors": request.query_params.get("errors"),
        "err": request.query_params.get("err"),
    }
    return render(
        request, "people.html",
        viewer=viewer, org=org, people=people, people_by_id=people_by_id,
        departments=depts, dept_by_id=dept_by_id,
        sidebar=sidebar, base_url=base_url, flash=flash,
    )


async def _sidebar(db: AsyncSession, viewer: Person):
    from vynaris.web.routes.channels import _build_sidebar
    return await _build_sidebar(db, viewer)


@router.post("/people/new")
async def people_new(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    title: str = Form(""),
    level: str = Form("5"),
    level_label: str = Form(""),
    manager_id: str = Form(""),
    department_id: str = Form(""),
    role_description: str = Form(""),
    person_type: str = Form("employee"),
    role_type: str = Form("employee"),
    employee_number: str = Form(""),
    working_mode: str = Form(""),
    make_admin: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    mid: uuid.UUID | None = None
    if manager_id:
        try:
            mid = uuid.UUID(manager_id)
        except ValueError:
            mid = None
    did: uuid.UUID | None = None
    if department_id:
        try:
            did = uuid.UUID(department_id)
        except ValueError:
            did = None
    try:
        lvl = int(level)
    except (TypeError, ValueError):
        lvl = 5
    draft = PersonDraft(
        name=name,
        email=email,
        title=title,
        level=lvl,
        level_label=level_label,
        role_description=role_description,
        person_type=person_type,
        role_type=role_type,
        employee_number=employee_number,
        working_mode=working_mode,
        is_admin=bool(make_admin),
    )
    await create_person(
        db, org_id=viewer.org_id, draft=draft,
        manager_id=mid, department_id=did,
    )
    await db.commit()
    return RedirectResponse("/people", status_code=303)


@router.post("/people/import")
async def people_import(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    result = await bulk_import_people(db, org_id=viewer.org_id, csv_text=text)
    await db.commit()
    qs = (
        f"?imported={result.created_count}&skipped={result.skipped_count}"
        f"&errors={result.error_count}"
    )
    return RedirectResponse(f"/people{qs}", status_code=303)


@router.post("/people/{person_id}/manager")
async def people_reassign_manager(
    person_id: uuid.UUID,
    request: Request,
    manager_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    target = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id:
        return RedirectResponse("/people", status_code=303)
    new_mgr_id: uuid.UUID | None = None
    if manager_id:
        try:
            new_mgr_id = uuid.UUID(manager_id)
        except ValueError:
            new_mgr_id = None
    if new_mgr_id is not None:
        if new_mgr_id == target.id:
            return RedirectResponse("/people?err=self_manager", status_code=303)
        mgr = (await db.execute(select(Person).where(Person.id == new_mgr_id))).scalar_one_or_none()
        if mgr is None or mgr.org_id != viewer.org_id:
            return RedirectResponse("/people?err=unknown_manager", status_code=303)
        if _would_cycle(target.id, new_mgr_id, await _manager_chain(db, viewer.org_id)):
            return RedirectResponse("/people?err=cycle", status_code=303)
    target.manager_id = new_mgr_id
    await db.commit()
    return RedirectResponse("/people", status_code=303)


async def _manager_chain(db: AsyncSession, org_id: uuid.UUID) -> dict[uuid.UUID, uuid.UUID | None]:
    rows = (await db.execute(select(Person).where(Person.org_id == org_id))).scalars().all()
    return {p.id: p.manager_id for p in rows}


def _would_cycle(target_id: uuid.UUID, new_manager_id: uuid.UUID, chain: dict[uuid.UUID, uuid.UUID | None]) -> bool:
    # walking up from new_manager_id, we should never hit target_id
    cur: uuid.UUID | None = new_manager_id
    hops = 0
    while cur is not None and hops < 50:
        if cur == target_id:
            return True
        cur = chain.get(cur)
        hops += 1
    return False


@router.post("/me/agent/profile")
async def update_my_agent(
    request: Request,
    agent_name: str = Form(""),
    agent_emoji: str = Form("🤖"),
    agent_identity: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    viewer.agent_name = agent_name.strip()[:64]
    viewer.agent_emoji = (agent_emoji.strip() or "🤖")[:8]
    viewer.agent_identity = agent_identity.strip()[:500]
    await db.commit()
    # Bounce any running agent so next message rebuilds the system prompt
    from vynaris.agent.runtime import manager as agent_manager
    async with agent_manager._lock:
        stale = [k for k in agent_manager._agents if k[0] == viewer.id]
        for k in stale:
            a = agent_manager._agents.pop(k)
            try:
                await a.stop()
            except Exception:
                pass
    back = request.headers.get("referer") or "/"
    return RedirectResponse(back, status_code=303)


@router.post("/people/{person_id}/delete")
async def people_delete(person_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await require_admin(request, db)
    target = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id or target.id == viewer.id:
        return RedirectResponse("/people", status_code=303)
    await db.delete(target)
    await db.commit()
    return RedirectResponse("/people", status_code=303)


@router.post("/people/{person_id}/resend_invite")
async def resend_invite(person_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await require_admin(request, db)
    target = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id:
        return RedirectResponse("/people", status_code=303)
    target.invite_token = new_invite_token()
    await db.commit()
    return RedirectResponse("/people", status_code=303)


@router.get("/people/{person_id}", response_class=HTMLResponse)
async def person_detail(person_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    target = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id:
        return RedirectResponse("/people", status_code=303)
    from vynaris.db.models import Goal, Team, TeamMembership
    goals = (
        await db.execute(select(Goal).where(Goal.owner_id == target.id).order_by(Goal.created_at))
    ).scalars().all()
    manager = None
    if target.manager_id:
        manager = (await db.execute(select(Person).where(Person.id == target.manager_id))).scalar_one_or_none()
    reports = (
        await db.execute(select(Person).where(Person.manager_id == target.id).order_by(Person.name))
    ).scalars().all()
    team_ids = (
        await db.execute(select(TeamMembership.team_id).where(TeamMembership.person_id == target.id))
    ).scalars().all()
    teams = []
    if team_ids:
        teams = list(
            (await db.execute(select(Team).where(Team.id.in_(team_ids)).order_by(Team.name))).scalars().all()
        )
    sidebar = await _sidebar(db, viewer)
    return render(
        request, "person_detail.html",
        viewer=viewer, target=target, goals=goals, manager=manager, reports=reports,
        teams=teams, sidebar=sidebar,
    )
