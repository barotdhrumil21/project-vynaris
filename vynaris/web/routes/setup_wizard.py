from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.auth import hash_password, validate_password
from vynaris.db import get_db
from vynaris.db.models import Channel, ChannelMember, Org, Person
from vynaris.db.seed import AVATAR_COLORS
from vynaris.services.onboarding import PERSONA_PACKS, install_persona_pack
from vynaris.web.deps import current_person, issue_session_cookie
from vynaris.web.templating import render

router = APIRouter()


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:60] or "org"


async def _org_exists(db: AsyncSession) -> bool:
    return (await db.execute(select(Org).limit(1))).scalar_one_or_none() is not None


async def _create_default_channels(db: AsyncSession, org_id, admin_id) -> None:
    general = Channel(
        org_id=org_id, name="general", slug="general",
        description="Company-wide announcements and chatter.",
        kind="public", created_by_id=admin_id,
    )
    db.add(general)
    await db.flush()
    db.add(ChannelMember(channel_id=general.id, person_id=admin_id))

    # Personal agent DM channel for the admin
    agent_ch = Channel(
        org_id=org_id, name="Your agent", slug=f"agent-{admin_id}",
        description="Your private workspace with your AI agent.",
        kind="agent", agent_for_id=admin_id, created_by_id=admin_id,
    )
    db.add(agent_ch)
    await db.flush()
    db.add(ChannelMember(channel_id=agent_ch.id, person_id=admin_id))


@router.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request, db: AsyncSession = Depends(get_db)):
    if await _org_exists(db):
        return RedirectResponse("/login", status_code=303)
    return render(request, "auth/setup.html", error=None, values={})


@router.post("/setup", response_class=HTMLResponse)
async def setup_post(
    request: Request,
    org_name: str = Form(...),
    org_context: str = Form(""),
    admin_name: str = Form(...),
    admin_email: str = Form(...),
    admin_title: str = Form("Founder & CEO"),
    admin_role: str = Form(""),
    password: str = Form(...),
    confirm: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if await _org_exists(db):
        return RedirectResponse("/login", status_code=303)

    values = {
        "org_name": org_name, "org_context": org_context,
        "admin_name": admin_name, "admin_email": admin_email,
        "admin_title": admin_title, "admin_role": admin_role,
    }

    if password != confirm:
        return render(request, "auth/setup.html", error="Passwords don't match.", values=values)
    err = validate_password(password)
    if err:
        return render(request, "auth/setup.html", error=err, values=values)

    org = Org(name=org_name.strip(), slug=_slug(org_name), context=org_context.strip())
    db.add(org)
    await db.flush()

    admin = Person(
        org_id=org.id,
        name=admin_name.strip(),
        email=admin_email.strip().lower(),
        password_hash=hash_password(password),
        title=admin_title.strip() or "Founder & CEO",
        role_description=admin_role.strip() or "Runs the company. Focuses on outcomes across every team.",
        is_admin=True,
        avatar_color=AVATAR_COLORS[0],
    )
    db.add(admin)
    await db.flush()

    await _create_default_channels(db, org.id, admin.id)
    await db.commit()

    resp = RedirectResponse("/setup/persona", status_code=303)
    issue_session_cookie(resp, admin.id)
    return resp


@router.get("/setup/persona", response_class=HTMLResponse)
async def setup_persona_get(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None or not viewer.is_admin:
        return RedirectResponse("/", status_code=303)
    # Only show the picker for a fresh org (admin + no other people).
    peer_count = len(
        (await db.execute(select(Person).where(Person.org_id == viewer.org_id))).scalars().all()
    )
    if peer_count > 1:
        return RedirectResponse("/", status_code=303)
    return render(request, "auth/persona.html", viewer=viewer, packs=PERSONA_PACKS)


@router.post("/setup/persona")
async def setup_persona_post(
    request: Request,
    pack: str = Form("blank"),
    db: AsyncSession = Depends(get_db),
):
    viewer = await current_person(request, db)
    if viewer is None or not viewer.is_admin:
        return RedirectResponse("/", status_code=303)
    if pack and pack != "blank":
        try:
            await install_persona_pack(db, org_id=viewer.org_id, admin=viewer, pack=pack)
            await db.commit()
        except Exception:
            await db.rollback()
            return RedirectResponse("/setup/persona?err=install_failed", status_code=303)
    return RedirectResponse("/?welcome=1", status_code=303)
