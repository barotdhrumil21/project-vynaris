from __future__ import annotations

import uuid
from functools import lru_cache

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vynaris.config import get_settings
from vynaris.db import get_db
from vynaris.db.models import Org, Person

SESSION_COOKIE = "vyn_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30


@lru_cache(maxsize=1)
def _signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().vynaris_secret_key, salt="vynaris-session-v2")


def issue_session_cookie(response, person_id: uuid.UUID) -> None:
    token = _signer().dumps(str(person_id))
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=SESSION_MAX_AGE, httponly=True, samesite="lax",
        secure=False, path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


async def current_person(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Person | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        pid_raw = _signer().loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    try:
        pid = uuid.UUID(pid_raw)
    except (TypeError, ValueError):
        return None
    return (
        await db.execute(
            select(Person).options(selectinload(Person.org)).where(Person.id == pid)
        )
    ).scalar_one_or_none()


async def require_person(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Person:
    p = await current_person(request, db)
    if p is None:
        raise HTTPException(status_code=401, detail="login required")
    return p


async def require_admin(
    request: Request, db: AsyncSession = Depends(get_db)
) -> Person:
    p = await require_person(request, db)
    if not p.is_admin:
        raise HTTPException(status_code=403, detail="admin only")
    return p


async def get_first_org(db: AsyncSession) -> Org | None:
    return (await db.execute(select(Org).limit(1))).scalar_one_or_none()
