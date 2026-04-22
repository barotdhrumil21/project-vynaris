from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db import get_db
from vynaris.db.models import Org, Person, Team, TeamMembership
from vynaris.web.deps import current_person, require_admin
from vynaris.web.routes.channels import _build_sidebar
from vynaris.web.templating import render

router = APIRouter()


def _slugify(s: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return out[:80] or f"team-{uuid.uuid4().hex[:6]}"


async def _members_for(db: AsyncSession, team_id: uuid.UUID) -> list[TeamMembership]:
    return list(
        (await db.execute(select(TeamMembership).where(TeamMembership.team_id == team_id))).scalars().all()
    )


@router.get("/teams", response_class=HTMLResponse)
async def teams_list(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    org = (await db.execute(select(Org).where(Org.id == viewer.org_id))).scalar_one()
    teams = (
        await db.execute(select(Team).where(Team.org_id == org.id).order_by(Team.name))
    ).scalars().all()
    memberships_by_team: dict[uuid.UUID, list[TeamMembership]] = {}
    if teams:
        rows = (
            await db.execute(
                select(TeamMembership).where(TeamMembership.team_id.in_([t.id for t in teams]))
            )
        ).scalars().all()
        for m in rows:
            memberships_by_team.setdefault(m.team_id, []).append(m)
    people_by_id = {
        p.id: p for p in (await db.execute(select(Person).where(Person.org_id == org.id))).scalars().all()
    }
    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "teams.html",
        viewer=viewer, org=org, teams=teams,
        memberships_by_team=memberships_by_team, people_by_id=people_by_id,
        sidebar=sidebar,
    )


@router.post("/teams/new")
async def teams_new(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    lead_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    slug_base = _slugify(name)
    slug = slug_base
    n = 1
    while True:
        existing = (
            await db.execute(select(Team).where(Team.org_id == viewer.org_id, Team.slug == slug))
        ).scalar_one_or_none()
        if existing is None:
            break
        n += 1
        slug = f"{slug_base}-{n}"
    lid: uuid.UUID | None = None
    if lead_id:
        try:
            lid = uuid.UUID(lead_id)
        except ValueError:
            lid = None
    team = Team(
        org_id=viewer.org_id,
        name=name.strip()[:128],
        slug=slug,
        description=description.strip(),
        lead_id=lid,
    )
    db.add(team)
    await db.flush()
    if lid is not None:
        db.add(TeamMembership(team_id=team.id, person_id=lid, role="lead"))
    await db.commit()
    return RedirectResponse(f"/teams/{team.id}", status_code=303)


@router.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_detail(team_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if team is None or team.org_id != viewer.org_id:
        return RedirectResponse("/teams", status_code=303)
    memberships = await _members_for(db, team.id)
    member_ids = [m.person_id for m in memberships]
    people = list(
        (await db.execute(select(Person).where(Person.org_id == team.org_id).order_by(Person.name))).scalars().all()
    )
    people_by_id = {p.id: p for p in people}
    non_members = [p for p in people if p.id not in member_ids]
    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "team_detail.html",
        viewer=viewer, team=team, memberships=memberships,
        people_by_id=people_by_id, non_members=non_members, sidebar=sidebar,
    )


@router.post("/teams/{team_id}/members")
async def team_add_member(
    team_id: uuid.UUID, request: Request,
    person_id: str = Form(...),
    role: str = Form("member"),
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if team is None or team.org_id != viewer.org_id:
        return RedirectResponse("/teams", status_code=303)
    try:
        pid = uuid.UUID(person_id)
    except ValueError:
        return RedirectResponse(f"/teams/{team.id}", status_code=303)
    target = (await db.execute(select(Person).where(Person.id == pid))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id:
        return RedirectResponse(f"/teams/{team.id}", status_code=303)
    existing = (
        await db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team.id, TeamMembership.person_id == pid
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(TeamMembership(team_id=team.id, person_id=pid, role=role.strip()[:48] or "member"))
        await db.commit()
    return RedirectResponse(f"/teams/{team.id}", status_code=303)


@router.post("/teams/{team_id}/members/{person_id}/delete")
async def team_remove_member(
    team_id: uuid.UUID, person_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if team is None or team.org_id != viewer.org_id:
        return RedirectResponse("/teams", status_code=303)
    m = (
        await db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team.id, TeamMembership.person_id == person_id
            )
        )
    ).scalar_one_or_none()
    if m is not None:
        await db.delete(m)
    if team.lead_id == person_id:
        team.lead_id = None
    await db.commit()
    return RedirectResponse(f"/teams/{team.id}", status_code=303)


@router.post("/teams/{team_id}/lead")
async def team_set_lead(
    team_id: uuid.UUID, request: Request,
    lead_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if team is None or team.org_id != viewer.org_id:
        return RedirectResponse("/teams", status_code=303)
    if not lead_id:
        team.lead_id = None
        await db.commit()
        return RedirectResponse(f"/teams/{team.id}", status_code=303)
    try:
        lid = uuid.UUID(lead_id)
    except ValueError:
        return RedirectResponse(f"/teams/{team.id}", status_code=303)
    target = (await db.execute(select(Person).where(Person.id == lid))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id:
        return RedirectResponse(f"/teams/{team.id}", status_code=303)
    team.lead_id = lid
    # ensure lead is a member
    existing = (
        await db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team.id, TeamMembership.person_id == lid
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(TeamMembership(team_id=team.id, person_id=lid, role="lead"))
    else:
        existing.role = "lead"
    await db.commit()
    return RedirectResponse(f"/teams/{team.id}", status_code=303)


@router.post("/teams/{team_id}/delete")
async def team_delete(team_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await require_admin(request, db)
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if team is None or team.org_id != viewer.org_id:
        return RedirectResponse("/teams", status_code=303)
    await db.delete(team)
    await db.commit()
    return RedirectResponse("/teams", status_code=303)
