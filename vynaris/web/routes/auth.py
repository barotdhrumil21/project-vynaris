from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.auth import hash_password, validate_password, verify_password
from vynaris.db import get_db
from vynaris.db.models import Org, Person
from vynaris.web.deps import clear_session_cookie, current_person, issue_session_cookie
from vynaris.web.templating import render

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, db: AsyncSession = Depends(get_db)):
    org = (await db.execute(select(Org).limit(1))).scalar_one_or_none()
    if org is None:
        return RedirectResponse("/setup", status_code=303)
    person = await current_person(request, db)
    if person is not None:
        return RedirectResponse("/", status_code=303)
    return render(request, "auth/login.html", org=org, error=None, email="")


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    org = (await db.execute(select(Org).limit(1))).scalar_one_or_none()
    if org is None:
        return RedirectResponse("/setup", status_code=303)
    email_norm = email.strip().lower()
    person = (
        await db.execute(
            select(Person).where(Person.org_id == org.id, Person.email == email_norm)
        )
    ).scalar_one_or_none()
    if person is None or not verify_password(password, person.password_hash):
        return render(
            request, "auth/login.html",
            org=org, error="Email or password didn't match.", email=email_norm,
        )
    resp = RedirectResponse("/", status_code=303)
    issue_session_cookie(resp, person.id)
    return resp


@router.post("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=303)
    clear_session_cookie(resp)
    return resp


@router.get("/signup/{token}", response_class=HTMLResponse)
async def accept_invite_get(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    person = (
        await db.execute(select(Person).where(Person.invite_token == token))
    ).scalar_one_or_none()
    if person is None:
        return render(request, "auth/invite_invalid.html", error="This invite is invalid or has already been used.")
    org = (await db.execute(select(Org).where(Org.id == person.org_id))).scalar_one()
    return render(request, "auth/accept_invite.html", person=person, org=org, token=token, error=None)


@router.post("/signup/{token}", response_class=HTMLResponse)
async def accept_invite_post(
    token: str,
    request: Request,
    password: str = Form(...),
    confirm: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    person = (
        await db.execute(select(Person).where(Person.invite_token == token))
    ).scalar_one_or_none()
    if person is None:
        return render(request, "auth/invite_invalid.html", error="This invite is invalid or has already been used.")
    org = (await db.execute(select(Org).where(Org.id == person.org_id))).scalar_one()
    if password != confirm:
        return render(
            request, "auth/accept_invite.html",
            person=person, org=org, token=token, error="Passwords don't match.",
        )
    err = validate_password(password)
    if err:
        return render(request, "auth/accept_invite.html", person=person, org=org, token=token, error=err)
    person.password_hash = hash_password(password)
    person.invite_token = None
    await db.commit()
    resp = RedirectResponse("/", status_code=303)
    issue_session_cookie(resp, person.id)
    return resp
