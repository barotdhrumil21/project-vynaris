"""External-platform links. `/channels` is the place to connect Discord / WhatsApp / …

The Slack-like in-app chat surface is gone — every user conversation happens on
an external platform via `vynaris/adapters/`.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.adapters import registry as adapter_registry
from vynaris.adapters.base import AdapterStatus
from vynaris.config import get_settings
from vynaris.db import get_db
from vynaris.db.models import ExternalLink, Org, Person
from vynaris.services import external_links as link_svc
from vynaris.web.deps import current_person
from vynaris.web.templating import render

router = APIRouter()


# Backwards-compatible no-op — legacy routes still pass `sidebar=…` to render().
async def _build_sidebar(db: AsyncSession, viewer: Person) -> dict:  # noqa: ARG001
    return {}


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    org = (await db.execute(select(Org).limit(1))).scalar_one_or_none()
    if org is None:
        return RedirectResponse("/setup", status_code=303)
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/goals", status_code=303)


@router.get("/channels", response_class=HTMLResponse)
async def channels_page(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)

    my_links = {
        row.platform: row for row in await link_svc.list_links_for_person(viewer.id)
    }

    cards = []
    for platform, adapter in adapter_registry.items():
        info = adapter.info()
        link = my_links.get(platform)
        cards.append({
            "platform": platform,
            "display_name": info.display_name,
            "icon": info.icon,
            "status": info.status.value,
            "detail": info.detail,
            "link": link,
            "pending_code": link.link_code if (link and link.verified_at is None) else "",
            "verified": link.verified_at is not None if link else False,
            "external_handle": link.external_handle if (link and link.verified_at) else "",
        })

    settings = get_settings()
    return render(
        request, "channels.html",
        viewer=viewer, cards=cards,
        discord_invite_url=settings.discord_bot_invite_url,
    )


@router.post("/channels/{platform}/connect")
async def connect_platform(
    platform: str, request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    adapter = adapter_registry.get(platform)
    if adapter is None or adapter.status == AdapterStatus.DISABLED:
        return RedirectResponse("/channels?err=unavailable", status_code=303)
    await link_svc.generate_link_code(person_id=viewer.id, platform=platform)
    return RedirectResponse("/channels", status_code=303)


@router.post("/channels/{platform}/unlink")
async def unlink_platform(
    platform: str, request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    await link_svc.unlink(person_id=viewer.id, platform=platform)
    return RedirectResponse("/channels", status_code=303)
