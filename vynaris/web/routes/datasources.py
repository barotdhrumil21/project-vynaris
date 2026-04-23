"""Org-level data sources + per-employee scope grants (admin surface)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db import get_db
from vynaris.db.models import Department, Person
from vynaris.services import datasources as ds_svc
from vynaris.services import departments as dept_svc
from vynaris.web.deps import current_person, require_admin
from vynaris.web.routes.channels import _build_sidebar
from vynaris.web.templating import render

router = APIRouter()


# ── List + create ─────────────────────────────────────────────────────────────


@router.get("/datasources", response_class=HTMLResponse)
async def datasources_list(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    sources = await ds_svc.list_for_org(db, viewer.org_id)
    # count grants per source for the summary column
    counts: dict[uuid.UUID, int] = {}
    for ds in sources:
        grants = await ds_svc.grants_for_source(db, ds.id)
        counts[ds.id] = len(grants)
    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "datasources.html",
        viewer=viewer, sources=sources, counts=counts,
        kind_labels=ds_svc.KIND_LABELS,
        live_kinds=ds_svc.LIVE_KINDS,
        sidebar=sidebar,
    )


@router.post("/datasources/new")
async def datasources_new(
    request: Request,
    name: str = Form(...),
    kind: str = Form(...),
    description: str = Form(""),
    sqlite_path: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    conn: dict = {}
    if kind == ds_svc.KIND_SQLITE and sqlite_path.strip():
        conn["path"] = sqlite_path.strip()
    await ds_svc.create(
        db, org_id=viewer.org_id,
        name=name.strip(), kind=kind.strip(),
        description=description.strip(),
        connection=conn, created_by_id=viewer.id,
    )
    await db.commit()
    return RedirectResponse("/datasources", status_code=303)


# ── Detail + grants ───────────────────────────────────────────────────────────


@router.get("/datasources/{ds_id}", response_class=HTMLResponse)
async def datasources_detail(
    ds_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    ds = await ds_svc.get(db, ds_id)
    if ds is None or ds.org_id != viewer.org_id:
        return RedirectResponse("/datasources", status_code=303)
    grants = await ds_svc.grants_for_source(db, ds.id)
    grants_by_person: dict[uuid.UUID, object] = {g.person_id: g for g in grants}
    people = list(
        (
            await db.execute(
                select(Person).where(Person.org_id == viewer.org_id).order_by(Person.name)
            )
        ).scalars().all()
    )
    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "datasource_detail.html",
        viewer=viewer, ds=ds, people=people, grants_by_person=grants_by_person,
        kind_labels=ds_svc.KIND_LABELS, sidebar=sidebar,
    )


@router.post("/datasources/{ds_id}/grants")
async def datasources_grants_update(
    ds_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    ds = await ds_svc.get(db, ds_id)
    if ds is None or ds.org_id != viewer.org_id:
        return RedirectResponse("/datasources", status_code=303)
    form = await request.form()
    # Collect per-person scope checkboxes. Each row is a submitted
    # person_id<uuid> + flags read_<uuid>, write_<uuid>, export_<uuid>, pii_<uuid>.
    people = list(
        (
            await db.execute(
                select(Person).where(Person.org_id == viewer.org_id)
            )
        ).scalars().all()
    )
    for p in people:
        pid = str(p.id)
        read = form.get(f"read_{pid}") == "on"
        write = form.get(f"write_{pid}") == "on"
        export = form.get(f"export_{pid}") == "on"
        pii = form.get(f"pii_{pid}") == "on"
        if not (read or write or export or pii):
            await ds_svc.revoke(db, data_source_id=ds.id, person_id=p.id)
        else:
            await ds_svc.grant(
                db, data_source_id=ds.id, person_id=p.id,
                can_read=read, can_write=write, can_export=export, can_see_pii=pii,
                granted_by_id=viewer.id,
            )
    await db.commit()
    return RedirectResponse(f"/datasources/{ds_id}", status_code=303)


@router.post("/datasources/{ds_id}/delete")
async def datasources_delete(
    ds_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    ds = await ds_svc.get(db, ds_id)
    if ds is None or ds.org_id != viewer.org_id:
        return RedirectResponse("/datasources", status_code=303)
    await db.delete(ds)
    await db.commit()
    return RedirectResponse("/datasources", status_code=303)


# ── Departments (needed by goal create + people forms) ───────────────────────


@router.get("/departments", response_class=HTMLResponse)
async def departments_list(request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    depts = await dept_svc.list_for_org(db, viewer.org_id)
    counts: dict[uuid.UUID, int] = {}
    for d in depts:
        counts[d.id] = len(await dept_svc.members(db, d.id))
    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "departments.html",
        viewer=viewer, depts=depts, counts=counts, sidebar=sidebar,
    )


@router.post("/departments/new")
async def departments_new(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await require_admin(request, db)
    await dept_svc.create(
        db, org_id=viewer.org_id,
        name=name.strip(), description=description.strip(),
    )
    await db.commit()
    return RedirectResponse("/departments", status_code=303)
