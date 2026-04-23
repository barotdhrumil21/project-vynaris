from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db import get_db
from vynaris.db.models import Goal, GoalWatcher, KeyResult, Message, Org, Person
from vynaris.services import goals as gsvc
from vynaris.services.visibility import can_view_goal, transitive_reports
from vynaris.web.deps import current_person, require_admin
from vynaris.web.routes.channels import _build_sidebar
from vynaris.web.templating import render

router = APIRouter()


async def _viewer_or_redirect(request: Request, db: AsyncSession):
    viewer = await current_person(request, db)
    if viewer is None:
        return None, RedirectResponse("/login", status_code=303)
    return viewer, None


@router.get("/goals", response_class=HTMLResponse)
async def goals_list(request: Request, db: AsyncSession = Depends(get_db)):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect
    org = (await db.execute(select(Org).where(Org.id == viewer.org_id))).scalar_one()
    all_goals = (
        await db.execute(select(Goal).where(Goal.org_id == org.id).order_by(Goal.created_at))
    ).scalars().all()
    goals = [g for g in all_goals if await can_view_goal(db, viewer, g)]
    people_by_id = {
        p.id: p for p in (await db.execute(select(Person).where(Person.org_id == org.id))).scalars().all()
    }
    krs_by_goal: dict[uuid.UUID, list[KeyResult]] = {}
    if goals:
        all_krs = (
            await db.execute(
                select(KeyResult).where(KeyResult.goal_id.in_([g.id for g in goals])).order_by(KeyResult.sort, KeyResult.created_at)
            )
        ).scalars().all()
        for kr in all_krs:
            krs_by_goal.setdefault(kr.goal_id, []).append(kr)
    open_goals = [g for g in goals if g.state == "open"]
    closed_goals = [g for g in goals if g.state == "closed"]
    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "goals.html",
        viewer=viewer, org=org,
        open_goals=open_goals, closed_goals=closed_goals,
        people_by_id=people_by_id, krs_by_goal=krs_by_goal,
        sidebar=sidebar,
    )


@router.get("/g/new", response_class=HTMLResponse)
async def goal_new_form(request: Request, db: AsyncSession = Depends(get_db)):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect
    people = (
        await db.execute(select(Person).where(Person.org_id == viewer.org_id).order_by(Person.name))
    ).scalars().all()
    parents = (
        await db.execute(select(Goal).where(Goal.org_id == viewer.org_id, Goal.state == "open").order_by(Goal.created_at))
    ).scalars().all()
    from vynaris.services import datasources as ds_svc
    from vynaris.services import departments as dept_svc
    depts = await dept_svc.list_for_org(db, viewer.org_id)
    sources = await ds_svc.list_for_org(db, viewer.org_id)
    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "goal_new.html",
        viewer=viewer, people=people, parents=parents,
        departments=depts, sources=sources,
        error=None, values={}, sidebar=sidebar,
    )


@router.post("/g/new")
async def goal_new(request: Request, db: AsyncSession = Depends(get_db)):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect

    form = await request.form()
    values = {
        "title": form.get("title", ""),
        "description": form.get("description", ""),
        "success_criteria": form.get("success_criteria", ""),
        "owner_id": form.get("owner_id", ""),
        "owner_department_id": form.get("owner_department_id", ""),
        "parent_id": form.get("parent_id", ""),
        "deadline": form.get("deadline", ""),
        "visibility": form.get("visibility", "team"),
    }

    async def rerender(error: str):
        from vynaris.services import datasources as ds_svc
        from vynaris.services import departments as dept_svc
        people = (
            await db.execute(select(Person).where(Person.org_id == viewer.org_id).order_by(Person.name))
        ).scalars().all()
        parents = (
            await db.execute(select(Goal).where(Goal.org_id == viewer.org_id, Goal.state == "open").order_by(Goal.created_at))
        ).scalars().all()
        depts = await dept_svc.list_for_org(db, viewer.org_id)
        sources = await ds_svc.list_for_org(db, viewer.org_id)
        # echo submitted KRs back
        krs_in: list[dict] = []
        i = 0
        while True:
            name_key = f"kr_name_{i}"
            if name_key not in form:
                break
            krs_in.append({
                "name": form.get(name_key, ""),
                "unit": form.get(f"kr_unit_{i}", ""),
                "target_value": form.get(f"kr_target_{i}", ""),
                "current_value": form.get(f"kr_current_{i}", ""),
                "measurement_kind": form.get(f"kr_kind_{i}", "manual"),
                "path": form.get(f"kr_path_{i}", ""),
                "url": form.get(f"kr_url_{i}", ""),
                "expr": form.get(f"kr_expr_{i}", ""),
                "alias": form.get(f"kr_alias_{i}", ""),
                "cadence": form.get(f"kr_cadence_{i}", ""),
                "column": form.get(f"kr_column_{i}", ""),
                "json_path": form.get(f"kr_jsonpath_{i}", ""),
                "note": form.get(f"kr_note_{i}", ""),
            })
            i += 1
        sidebar = await _build_sidebar(db, viewer)
        return render(
            request, "goal_new.html",
            viewer=viewer, people=people, parents=parents,
            departments=depts, sources=sources,
            error=error, values=values, krs_in=krs_in, sidebar=sidebar,
        )

    title = values["title"].strip()
    if not title:
        return await rerender("Goal needs a title.")
    try:
        owner_id = uuid.UUID(values["owner_id"])
    except (ValueError, TypeError):
        return await rerender("Pick an owner for this goal.")
    owner = (await db.execute(select(Person).where(Person.id == owner_id))).scalar_one_or_none()
    if owner is None or owner.org_id != viewer.org_id:
        return await rerender("Owner not found in this org.")
    parent_uuid = None
    if values["parent_id"]:
        try:
            parent_uuid = uuid.UUID(values["parent_id"])
        except ValueError:
            parent_uuid = None
    deadline_d = None
    if values["deadline"]:
        try:
            deadline_d = date.fromisoformat(values["deadline"])
        except ValueError:
            deadline_d = None

    # Collect KRs from form — required, at least one with a real measurement
    krs: list[dict] = []
    i = 0
    while True:
        name_key = f"kr_name_{i}"
        if name_key not in form:
            break
        name = (form.get(name_key) or "").strip()
        if not name:
            i += 1
            continue
        kind = (form.get(f"kr_kind_{i}") or "manual").strip()
        cfg: dict = {}
        alias = (form.get(f"kr_alias_{i}") or "").strip()
        if alias:
            cfg["alias"] = alias
        cadence_raw = (form.get(f"kr_cadence_{i}") or "").strip()
        if cadence_raw:
            try:
                cfg["cadence_minutes"] = int(cadence_raw)
            except ValueError:
                pass
        if kind == "workspace_file":
            cfg["path"] = (form.get(f"kr_path_{i}") or "").strip()
            col = (form.get(f"kr_column_{i}") or "").strip()
            if col:
                cfg["column"] = col
        elif kind == "url":
            cfg["url"] = (form.get(f"kr_url_{i}") or "").strip()
            jp = (form.get(f"kr_jsonpath_{i}") or "").strip()
            if jp:
                cfg["json_path"] = jp
        elif kind == "formula":
            cfg["expr"] = (form.get(f"kr_expr_{i}") or "").strip()
        note = (form.get(f"kr_note_{i}") or "").strip()
        if note:
            cfg["note"] = note
        krs.append({
            "name": name,
            "unit": (form.get(f"kr_unit_{i}") or "").strip(),
            "target_value": form.get(f"kr_target_{i}") or None,
            "current_value": form.get(f"kr_current_{i}") or None,
            "measurement_kind": kind,
            "measurement_config": cfg,
        })
        i += 1

    if not krs:
        return await rerender("Goals must have at least one Key Result with a measurement source.")

    visibility = values["visibility"] if values["visibility"] in ("private", "team", "org", "viewers") else "team"
    viewer_ids: list[str] = []
    if visibility == "viewers":
        for raw_id in form.getlist("viewer_ids"):
            try:
                viewer_ids.append(str(uuid.UUID(raw_id)))
            except (ValueError, AttributeError):
                continue
        if not viewer_ids:
            return await rerender('Visibility "viewers" needs at least one allowed person.')
    owner_dept_uuid: uuid.UUID | None = None
    if values["owner_department_id"]:
        try:
            owner_dept_uuid = uuid.UUID(values["owner_department_id"])
        except ValueError:
            owner_dept_uuid = None

    ds_ids: list[uuid.UUID] = []
    for raw_id in form.getlist("data_source_ids"):
        try:
            ds_ids.append(uuid.UUID(raw_id))
        except (ValueError, AttributeError):
            continue

    try:
        goal = await gsvc.create_goal(
            db,
            org_id=viewer.org_id,
            owner_id=owner_id,
            owner_department_id=owner_dept_uuid,
            author_id=viewer.id,
            title=title,
            description=values["description"],
            success_criteria=values["success_criteria"],
            parent_id=parent_uuid,
            deadline=deadline_d,
            visibility=visibility,
            viewer_ids=viewer_ids,
            key_results=krs,
            data_source_ids=ds_ids,
        )
    except ValueError as e:
        return await rerender(str(e))

    await db.commit()
    await db.refresh(goal)
    return RedirectResponse("/goals", status_code=303)


@router.get("/g/{goal_id}")
async def goal_redirect(goal_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.channel_id is None:
        return RedirectResponse("/goals", status_code=303)
    return RedirectResponse("/goals", status_code=303)


@router.post("/g/{goal_id}/close")
async def goal_close(
    goal_id: uuid.UUID, request: Request,
    note: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.org_id != viewer.org_id:
        return RedirectResponse("/goals", status_code=303)
    if not (viewer.is_admin or g.owner_id == viewer.id):
        return RedirectResponse("/goals", status_code=303)
    await gsvc.close_goal(db, goal=g, actor_id=viewer.id, is_agent=False, note=note)
    await db.commit()
    return RedirectResponse("/goals", status_code=303)


@router.post("/g/{goal_id}/reopen")
async def goal_reopen(goal_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.org_id != viewer.org_id:
        return RedirectResponse("/goals", status_code=303)
    if not (viewer.is_admin or g.owner_id == viewer.id):
        return RedirectResponse("/goals", status_code=303)
    await gsvc.reopen_goal(db, goal=g, actor_id=viewer.id)
    await db.commit()
    return RedirectResponse("/goals", status_code=303)


async def _reassign_targets(db: AsyncSession, viewer: Person, goal: Goal) -> set[uuid.UUID] | None:
    """Return the set of person ids viewer is allowed to reassign this goal to, or None if they cannot reassign at all."""
    if viewer.is_admin:
        rows = (
            await db.execute(select(Person.id).where(Person.org_id == viewer.org_id))
        ).scalars().all()
        return set(rows)
    if goal.created_by_id == viewer.id:
        reports = await transitive_reports(db, viewer.id)
        return reports | {viewer.id}
    return None


@router.post("/g/{goal_id}/reassign")
async def goal_reassign(
    goal_id: uuid.UUID, request: Request,
    owner_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.org_id != viewer.org_id:
        return RedirectResponse("/goals", status_code=303)
    allowed = await _reassign_targets(db, viewer, g)
    if allowed is None:
        return RedirectResponse("/goals", status_code=303)
    try:
        new_owner = uuid.UUID(owner_id)
    except ValueError:
        return RedirectResponse("/goals", status_code=303)
    if new_owner not in allowed:
        return RedirectResponse("/goals", status_code=303)
    target = (await db.execute(select(Person).where(Person.id == new_owner))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id:
        return RedirectResponse("/goals", status_code=303)
    if new_owner != g.owner_id:
        await gsvc.reassign_goal(db, goal=g, new_owner_id=new_owner, actor_id=viewer.id)
        await db.commit()
    return RedirectResponse("/goals", status_code=303)


@router.post("/g/{goal_id}/delete")
async def goal_delete(goal_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await require_admin(request, db)
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g and g.org_id == viewer.org_id:
        await db.delete(g)
        await db.commit()
    return RedirectResponse("/goals", status_code=303)


@router.post("/g/{goal_id}/check_in")
async def goal_check_in(
    goal_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    body: dict = Body(...),
):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return JSONResponse({"error": "auth"}, status_code=401)
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.org_id != viewer.org_id:
        return JSONResponse({"error": "not_found"}, status_code=404)
    if not (viewer.is_admin or g.owner_id == viewer.id):
        # only owner or admin can post check-ins
        return JSONResponse({"error": "forbidden"}, status_code=403)
    narrative = str(body.get("narrative", "")).strip()
    if not narrative:
        return JSONResponse({"error": "narrative required"}, status_code=400)
    blockers = body.get("blockers") or []
    next_steps = body.get("next_steps") or []
    kr_updates = body.get("kr_updates") or []
    if not isinstance(blockers, list):
        blockers = []
    if not isinstance(next_steps, list):
        next_steps = []
    if not isinstance(kr_updates, list):
        kr_updates = []
    msg = await gsvc.post_check_in(
        db, goal=g, author_id=viewer.id, is_agent=False,
        narrative=narrative, blockers=blockers, next_steps=next_steps, kr_updates=kr_updates,
    )
    await db.commit()
    return {"ok": True, "id": str(msg.id)}


@router.post("/g/{goal_id}/ask")
async def goal_ask(
    goal_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    body: dict = Body(...),
):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return JSONResponse({"error": "auth"}, status_code=401)
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.org_id != viewer.org_id:
        return JSONResponse({"error": "not_found"}, status_code=404)
    question = str(body.get("content", "")).strip()
    if not question:
        return JSONResponse({"error": "empty"}, status_code=400)
    priority = str(body.get("priority", "normal"))
    msg = await gsvc.post_question(
        db, goal=g, author_id=viewer.id, is_agent=False,
        question=question, priority=priority,
    )
    await db.commit()
    return {"ok": True, "id": str(msg.id)}


@router.post("/m/{message_id}/resolve")
async def message_resolve(
    message_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    body: dict = Body(...),
):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return JSONResponse({"error": "auth"}, status_code=401)
    q = (await db.execute(select(Message).where(Message.id == message_id))).scalar_one_or_none()
    if q is None or q.kind != "question" or q.resolved_at is not None:
        return JSONResponse({"error": "not_open_question"}, status_code=404)
    answer = str(body.get("answer", "")).strip()
    if not answer:
        return JSONResponse({"error": "empty"}, status_code=400)
    await gsvc.resolve_question(db, question=q, resolver_id=viewer.id, is_agent=False, answer=answer)
    await db.commit()
    return {"ok": True}


@router.post("/g/{goal_id}/krs/{kr_id}/update")
async def kr_update(
    goal_id: uuid.UUID, kr_id: uuid.UUID, request: Request,
    current_value: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.org_id != viewer.org_id:
        return RedirectResponse("/goals", status_code=303)
    if not (viewer.is_admin or g.owner_id == viewer.id):
        return RedirectResponse("/goals", status_code=303)
    kr = (await db.execute(select(KeyResult).where(KeyResult.id == kr_id, KeyResult.goal_id == g.id))).scalar_one_or_none()
    if kr is None:
        return RedirectResponse("/goals", status_code=303)
    try:
        new_val = float(current_value)
    except (TypeError, ValueError):
        return RedirectResponse("/goals", status_code=303)
    await gsvc.update_kr_value(db, kr=kr, new_value=new_val, actor_id=viewer.id, is_agent=False, goal=g)
    await db.commit()
    return RedirectResponse("/goals", status_code=303)


@router.post("/g/{goal_id}/watch")
async def goal_watch(
    goal_id: uuid.UUID, request: Request,
    person_id: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.org_id != viewer.org_id:
        return RedirectResponse("/goals", status_code=303)
    # Determine who to add as a watcher. Default: the viewer themself.
    target_id = viewer.id
    if person_id:
        if not (viewer.is_admin or g.owner_id == viewer.id):
            return RedirectResponse("/goals", status_code=303)
        try:
            target_id = uuid.UUID(person_id)
        except ValueError:
            return RedirectResponse("/goals", status_code=303)
        target = (await db.execute(select(Person).where(Person.id == target_id))).scalar_one_or_none()
        if target is None or target.org_id != viewer.org_id:
            return RedirectResponse("/goals", status_code=303)
    if not await can_view_goal(db, viewer, g) and target_id == viewer.id:
        # viewer can't even see this goal — refuse silent self-watch
        return RedirectResponse("/goals", status_code=303)
    existing = (
        await db.execute(
            select(GoalWatcher).where(
                GoalWatcher.goal_id == g.id, GoalWatcher.person_id == target_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(GoalWatcher(goal_id=g.id, person_id=target_id))
        await gsvc.post_system_event(
            db, channel_id=g.channel_id, actor_id=viewer.id,
            event="watcher_added",
            summary=f"Watcher added: {target_id}",
            extra={"person_id": str(target_id)},
        )
        await db.commit()
    return RedirectResponse("/goals", status_code=303)


@router.post("/g/{goal_id}/unwatch/{person_id}")
async def goal_unwatch(
    goal_id: uuid.UUID, person_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.org_id != viewer.org_id:
        return RedirectResponse("/goals", status_code=303)
    # owner/admin can remove any watcher; anyone can remove themself
    if not (viewer.is_admin or g.owner_id == viewer.id or viewer.id == person_id):
        return RedirectResponse("/goals", status_code=303)
    w = (
        await db.execute(
            select(GoalWatcher).where(
                GoalWatcher.goal_id == g.id, GoalWatcher.person_id == person_id,
            )
        )
    ).scalar_one_or_none()
    if w is not None:
        await db.delete(w)
        await gsvc.post_system_event(
            db, channel_id=g.channel_id, actor_id=viewer.id,
            event="watcher_removed",
            summary=f"Watcher removed: {person_id}",
            extra={"person_id": str(person_id)},
        )
        await db.commit()
    return RedirectResponse("/goals", status_code=303)


@router.post("/g/{goal_id}/krs/{kr_id}/refresh")
async def kr_refresh_now(
    goal_id: uuid.UUID, kr_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer, redirect = await _viewer_or_redirect(request, db)
    if redirect is not None:
        return redirect
    g = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one_or_none()
    if g is None or g.org_id != viewer.org_id:
        return RedirectResponse("/goals", status_code=303)
    if not (viewer.is_admin or g.owner_id == viewer.id):
        return RedirectResponse("/goals", status_code=303)
    kr = (await db.execute(select(KeyResult).where(KeyResult.id == kr_id, KeyResult.goal_id == g.id))).scalar_one_or_none()
    if kr is None:
        return RedirectResponse("/goals", status_code=303)
    from vynaris.services.kr_refresh import refresh_kr
    await refresh_kr(db, kr=kr, goal=g, force=True)
    await db.commit()
    return RedirectResponse("/goals", status_code=303)
