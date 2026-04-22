from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.agent.skill_loader import load_personal_skills, load_platform_skills
from vynaris.db import get_db
from vynaris.web.deps import current_person
from vynaris.web.routes.channels import _build_sidebar
from vynaris.web.templating import render

router = APIRouter()


@router.get("/skills", response_class=HTMLResponse)
async def skills_page(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    platform = [{"name": s.name, "description": s.description, "tier": s.tier, "body": s.body()} for s in load_platform_skills()]
    personal = [{"name": s.name, "description": s.description, "tier": s.tier, "body": s.body()} for s in load_personal_skills(str(viewer.id))]
    sidebar = await _build_sidebar(db, viewer)
    return render(request, "skills.html", viewer=viewer, platform=platform, personal=personal, sidebar=sidebar)
