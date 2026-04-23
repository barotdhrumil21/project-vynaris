"""Integrations grid + Gmail OAuth flow (the one connector that actually works)."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.config import get_settings
from vynaris.db import get_db
from vynaris.integrations import gmail as gmail_svc
from vynaris.services import integrations as isvc
from vynaris.web.deps import current_person
from vynaris.web.templating import render

router = APIRouter()

_OAUTH_STATE: dict[str, dict] = {}


@router.get("/integrations", response_class=HTMLResponse)
async def integrations_page(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    rows = await isvc.list_for_org(viewer.org_id)
    categories: dict[str, list] = {}
    for r in rows:
        categories.setdefault(r["spec"].category, []).append(r)
    settings = get_settings()
    return render(
        request, "integrations.html",
        viewer=viewer, categories=categories,
        gmail_configured=bool(settings.gmail_client_id and settings.gmail_client_secret),
    )


@router.post("/integrations/{kind}/disconnect")
async def disconnect(kind: str, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    await isvc.disconnect(viewer.org_id, kind)
    return RedirectResponse("/integrations", status_code=303)


@router.get("/integrations/gmail/connect")
async def gmail_connect(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    if not gmail_svc.is_configured():
        return RedirectResponse("/integrations?err=gmail_not_configured", status_code=303)
    state = secrets.token_urlsafe(24)
    _OAUTH_STATE[state] = {"viewer_id": str(viewer.id), "org_id": str(viewer.org_id)}
    return RedirectResponse(gmail_svc.auth_url(state), status_code=303)


@router.get("/integrations/gmail/callback")
async def gmail_callback(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    state = request.query_params.get("state", "")
    code = request.query_params.get("code", "")
    entry = _OAUTH_STATE.pop(state, None)
    if entry is None or entry.get("viewer_id") != str(viewer.id):
        return RedirectResponse("/integrations?err=invalid_state", status_code=303)
    try:
        cfg = await gmail_svc.exchange_code(code)
        await isvc.set_connected(
            org_id=viewer.org_id, kind="gmail", config=cfg, connected_by_id=viewer.id,
        )
    except Exception:
        return RedirectResponse("/integrations?err=gmail_exchange_failed", status_code=303)
    return RedirectResponse("/integrations?ok=gmail", status_code=303)
