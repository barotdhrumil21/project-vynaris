from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Body, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from vynaris.agent.runtime import manager as agent_manager
from vynaris.db import get_db
from vynaris.db.models import Channel, ChannelMember, Goal, GoalWatcher, KeyResult, Message, Person
from vynaris.services import channels as chsvc
from vynaris.services.stream_bus import bus, channel_bus_key
from vynaris.web.deps import current_person, require_admin
from vynaris.web.templating import render

router = APIRouter()


async def _get_viewer(request: Request, db: AsyncSession) -> Person | None:
    return await current_person(request, db)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    from vynaris.db.models import Org
    org = (await db.execute(select(Org).limit(1))).scalar_one_or_none()
    if org is None:
        return RedirectResponse("/setup", status_code=303)
    viewer = await _get_viewer(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    # Land on agent channel for a first-visit experience
    agent_ch = await chsvc.get_or_create_agent_channel(db, viewer)
    await db.commit()
    return RedirectResponse(f"/c/{agent_ch.id}", status_code=303)


@router.get("/c/{channel_id}", response_class=HTMLResponse)
async def channel_view(channel_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await _get_viewer(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    channel = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if channel is None or not await chsvc.can_view_channel(db, viewer, channel):
        return RedirectResponse("/", status_code=303)

    # materialize membership for public channels on view
    if channel.kind == "public":
        existing = (
            await db.execute(
                select(ChannelMember).where(
                    ChannelMember.channel_id == channel.id, ChannelMember.person_id == viewer.id,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(ChannelMember(channel_id=channel.id, person_id=viewer.id))
            await db.commit()

    messages = (
        await db.execute(
            select(Message).where(Message.channel_id == channel.id).order_by(Message.created_at).limit(400)
        )
    ).scalars().all()

    sidebar = await _build_sidebar(db, viewer)
    people_by_id = await _people_by_id(db, viewer.org_id)
    counterpart = await chsvc.dm_counterpart(db, channel, viewer) if channel.kind == "dm" else None

    goal = None
    krs: list[KeyResult] = []
    open_questions_count = 0
    reassign_targets: set = set()
    watchers: list[Person] = []
    viewer_is_watcher = False
    kr_viz: dict[uuid.UUID, dict] = {}
    if channel.kind == "goal":
        if channel.goal_id is not None:
            goal = (await db.execute(select(Goal).where(Goal.id == channel.goal_id))).scalar_one_or_none()
        if goal is not None:
            krs = (
                await db.execute(select(KeyResult).where(KeyResult.goal_id == goal.id).order_by(KeyResult.sort))
            ).scalars().all()
            open_questions_count = len((
                await db.execute(
                    select(Message).where(
                        Message.channel_id == channel.id,
                        Message.kind == "question",
                        Message.resolved_at.is_(None),
                    )
                )
            ).scalars().all())
            from vynaris.web.routes.goals import _reassign_targets
            allowed = await _reassign_targets(db, viewer, goal)
            reassign_targets = allowed or set()
            watcher_rows = (
                await db.execute(select(GoalWatcher).where(GoalWatcher.goal_id == goal.id))
            ).scalars().all()
            watcher_ids = [w.person_id for w in watcher_rows]
            viewer_is_watcher = viewer.id in watcher_ids
            if watcher_ids:
                watchers = list(
                    (await db.execute(select(Person).where(Person.id.in_(watcher_ids)))).scalars().all()
                )
            # Per-KR viz: inline sparkline + freshness pill for the goal header.
            from vynaris.services.data_sources import kr_freshness, kr_value_history, sparkline_svg
            for kr in krs:
                history = await kr_value_history(db, kr_id=kr.id, goal=goal, limit=16)
                kr_viz[kr.id] = {
                    "sparkline": sparkline_svg(history, width=96, height=22) if len(history) >= 2 else "",
                    "freshness": kr_freshness(kr),
                    "history_len": len(history),
                }

    # Mention index for the composer typeahead. Starts with @agent (self-shortcut),
    # then everyone in the org sorted so the viewer and channel members surface first.
    channel_member_ids = set(
        (
            await db.execute(
                select(ChannelMember.person_id).where(ChannelMember.channel_id == channel.id)
            )
        ).scalars().all()
    )
    mention_index = [{
        "handle": "agent",
        "name": "your own agent",
        "title": "shortcut — fires your personal agent",
        "avatar_color": "#6366f1",
        "is_self_shortcut": True,
    }]
    org_people = sorted(
        people_by_id.values(),
        key=lambda p: (
            0 if p.id == viewer.id else (1 if p.id in channel_member_ids else 2),
            p.name.lower(),
        ),
    )
    for p in org_people:
        if not p.handle:
            continue
        mention_index.append({
            "handle": p.handle,
            "name": p.name,
            "title": p.title or "",
            "avatar_color": p.avatar_color,
            "is_self_shortcut": False,
        })

    return render(
        request, "channel.html",
        viewer=viewer, channel=channel, messages=messages, sidebar=sidebar,
        people_by_id=people_by_id, counterpart=counterpart,
        goal=goal, krs=krs, kr_viz=kr_viz, open_questions_count=open_questions_count,
        reassign_targets=reassign_targets,
        watchers=watchers, viewer_is_watcher=viewer_is_watcher,
        mention_index=mention_index,
    )


async def _people_by_id(db: AsyncSession, org_id: uuid.UUID) -> dict:
    rows = (await db.execute(select(Person).where(Person.org_id == org_id))).scalars().all()
    return {p.id: p for p in rows}


async def _build_sidebar(db: AsyncSession, viewer: Person) -> dict:
    channels = await chsvc.get_viewer_channels(db, viewer)
    agent_ch = next((c for c in channels if c.kind == "agent" and c.agent_for_id == viewer.id), None)
    if agent_ch is None:
        agent_ch = await chsvc.get_or_create_agent_channel(db, viewer)
        await db.commit()
        channels.append(agent_ch)
    # surface the viewer's chosen agent name in the sidebar
    agent_ch.name = viewer.display_agent_name

    public = [c for c in channels if c.kind == "public"]
    private = [c for c in channels if c.kind == "private"]
    dms = [c for c in channels if c.kind == "dm"]
    people_by_id = await _people_by_id(db, viewer.org_id)
    for dm in dms:
        counterpart = await chsvc.dm_counterpart(db, dm, viewer)
        dm._dm_counterpart = counterpart  # attach for template

    all_people = [p for p in people_by_id.values() if p.id != viewer.id]
    existing_dm_counterpart_ids = {getattr(dm, "_dm_counterpart", None).id for dm in dms if getattr(dm, "_dm_counterpart", None)}
    start_dm_targets = [p for p in all_people if p.id not in existing_dm_counterpart_ids]
    start_dm_targets.sort(key=lambda p: p.name.lower())

    return {
        "public": public,
        "private": private,
        "dms": dms,
        "agent": agent_ch,
        "start_dm_targets": start_dm_targets,
        "people_by_id": people_by_id,
    }


@router.post("/c/new")
async def channel_new(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    visibility: str = Form("public"),
    db: AsyncSession = Depends(get_db),
):
    viewer = await _get_viewer(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    kind = "private" if visibility == "private" else "public"
    base_slug = chsvc.slug_from_name(name)
    slug = base_slug
    n = 1
    while True:
        existing = (
            await db.execute(select(Channel).where(Channel.org_id == viewer.org_id, Channel.slug == slug))
        ).scalar_one_or_none()
        if existing is None:
            break
        n += 1
        slug = f"{base_slug}-{n}"
    ch = Channel(
        org_id=viewer.org_id, name=name.strip()[:80], slug=slug,
        description=description.strip()[:500], kind=kind, created_by_id=viewer.id,
    )
    db.add(ch)
    await db.flush()
    db.add(ChannelMember(channel_id=ch.id, person_id=viewer.id))
    await db.commit()
    return RedirectResponse(f"/c/{ch.id}", status_code=303)


@router.post("/c/{channel_id}/invite")
async def channel_invite(
    channel_id: uuid.UUID, request: Request,
    person_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    viewer = await _get_viewer(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    channel = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if channel is None or channel.org_id != viewer.org_id:
        return RedirectResponse("/", status_code=303)
    try:
        pid = uuid.UUID(person_id)
    except ValueError:
        return RedirectResponse(f"/c/{channel.id}", status_code=303)
    target = (await db.execute(select(Person).where(Person.id == pid))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id:
        return RedirectResponse(f"/c/{channel.id}", status_code=303)
    existing = (
        await db.execute(
            select(ChannelMember).where(
                ChannelMember.channel_id == channel.id, ChannelMember.person_id == target.id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(ChannelMember(channel_id=channel.id, person_id=target.id))
        await db.commit()
    return RedirectResponse(f"/c/{channel.id}", status_code=303)


@router.get("/dm/{person_id}", response_class=HTMLResponse)
async def open_dm(person_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await _get_viewer(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    target = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id:
        return RedirectResponse("/", status_code=303)
    ch = await chsvc.find_or_create_dm(db, viewer, target)
    await db.commit()
    return RedirectResponse(f"/c/{ch.id}", status_code=303)


@router.post("/c/{channel_id}/send")
async def send_message(
    channel_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    body: dict = Body(...),
):
    viewer = await _get_viewer(request, db)
    if viewer is None:
        return JSONResponse({"error": "auth"}, status_code=401)
    channel = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if channel is None or not await chsvc.can_post_in(db, viewer, channel):
        return JSONResponse({"error": "forbidden"}, status_code=403)

    text = str(body.get("content", "")).strip()
    if not text:
        return JSONResponse({"error": "empty"}, status_code=400)

    msg = Message(
        channel_id=channel.id, person_id=viewer.id, is_agent=False,
        kind="text", content=text, extra={},
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    await bus.publish(channel_bus_key(channel.id), "message.new", {
        "id": str(msg.id),
        "channel_id": str(channel.id),
        "person_id": str(viewer.id),
        "is_agent": False,
        "kind": "text",
        "content": text,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    })

    # Dispatch agents:
    #   (a) Always fire the viewer's own agent in their private agent channel.
    #   (b) In every other channel, parse @handles and fire each matched person's agent.
    #       `@agent` is a shortcut for the speaker's own agent.
    if channel.kind == "agent" and channel.agent_for_id == viewer.id:
        agent = await agent_manager.for_person(viewer.id, viewer.org_id, channel_id=channel.id)
        await agent.send(text)
    else:
        mentioned = await _resolve_mentions(db, text, channel.org_id, viewer)
        for target in mentioned:
            # the target's agent must be able to see/post in this channel
            if not await chsvc.can_post_in(db, target, channel):
                continue
            self_mention = target.id == viewer.id
            prompt = _build_mention_prompt(
                target=target, viewer=viewer, channel=channel, text=text, self_mention=self_mention,
            )
            agent = await agent_manager.for_person(target.id, target.org_id, channel_id=channel.id)
            await agent.send(prompt)

    return {"ok": True, "id": str(msg.id)}


def _extract_handle_tokens(text: str) -> list[str]:
    """Lowercased, deduped @handle tokens in the text. Strips trailing punctuation."""
    import re
    tokens: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"(?:^|[^\w@])@([a-z0-9][a-z0-9-]{0,31})", text.lower()):
        h = m.group(1).rstrip("-")
        if h and h not in seen:
            seen.add(h)
            tokens.append(h)
    return tokens


async def _resolve_mentions(
    db: AsyncSession, text: str, org_id: uuid.UUID, viewer: Person,
) -> list[Person]:
    """Return the distinct list of Persons whose agents should fire for this message."""
    tokens = _extract_handle_tokens(text)
    if not tokens:
        return []
    results: list[Person] = []
    seen: set[uuid.UUID] = set()
    if "agent" in tokens:
        # speaker's own agent shortcut
        if viewer.id not in seen:
            results.append(viewer)
            seen.add(viewer.id)
        tokens = [t for t in tokens if t != "agent"]
    if tokens:
        rows = (
            await db.execute(
                select(Person).where(Person.org_id == org_id, Person.handle.in_(tokens))
            )
        ).scalars().all()
        # Preserve token order in the return list
        by_handle = {p.handle: p for p in rows}
        for t in tokens:
            p = by_handle.get(t)
            if p is not None and p.id not in seen:
                results.append(p)
                seen.add(p.id)
    return results


def _build_mention_prompt(
    *, target: Person, viewer: Person, channel: Channel, text: str, self_mention: bool,
) -> str:
    who = "your person" if self_mention else f"{viewer.name} (@{viewer.handle or viewer.email})"
    return (
        f"You were @mentioned in channel `{channel.name}` (channel_id `{channel.id}`, "
        f"kind=`{channel.kind}`) by {who}. Their message:\n\n---\n{text}\n---\n\n"
        f"Respond in that channel via `post_to_channel` when you're ready. "
        f"If it's trivial conversation, a short direct reply is enough. "
        f"If it needs research or artifact work, plan → act → observe → update as usual "
        f"and post the result back there."
    )


@router.get("/c/{channel_id}/stream")
async def channel_stream(channel_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    viewer = await _get_viewer(request, db)
    if viewer is None:
        return JSONResponse({"error": "auth"}, status_code=401)
    channel = (await db.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
    if channel is None or not await chsvc.can_view_channel(db, viewer, channel):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    key = channel_bus_key(channel.id)

    async def events():
        q = bus.subscribe(key)
        try:
            yield {"event": "ready", "data": json.dumps({"ok": True})}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                decoded = json.loads(payload)
                yield {"event": decoded["event"], "data": json.dumps(decoded["data"], default=str)}
        finally:
            bus.unsubscribe(key, q)

    return EventSourceResponse(events())
