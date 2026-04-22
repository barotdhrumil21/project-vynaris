"""Goal service: creation with channel, check-ins, questions, closes, KR updates."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db.models import Channel, ChannelMember, Goal, KeyResult, Message, Person
from vynaris.services.stream_bus import bus, channel_bus_key


def goal_slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return ("goal-" + s[:60]).rstrip("-") or f"goal-{uuid.uuid4().hex[:8]}"


async def _unique_channel_slug(db: AsyncSession, org_id: uuid.UUID, base: str) -> str:
    slug = base
    n = 1
    while True:
        exists = (
            await db.execute(select(Channel).where(Channel.org_id == org_id, Channel.slug == slug))
        ).scalar_one_or_none()
        if exists is None:
            return slug
        n += 1
        slug = f"{base}-{n}"


async def create_goal(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    owner_id: uuid.UUID,
    author_id: uuid.UUID,
    title: str,
    description: str = "",
    success_criteria: str = "",
    parent_id: uuid.UUID | None = None,
    deadline=None,
    visibility: str = "team",
    viewer_ids: list[uuid.UUID | str] | None = None,
    key_results: list[dict[str, Any]] | None = None,
) -> Goal:
    if not key_results:
        raise ValueError("At least one key result with a measurement source is required.")
    for i, kr in enumerate(key_results):
        if not (kr.get("name") or "").strip():
            raise ValueError(f"Key result #{i+1} needs a name.")
        mk = (kr.get("measurement_kind") or "manual").strip()
        if mk not in ("manual", "workspace_file", "url", "formula"):
            raise ValueError(f"Key result #{i+1}: unknown measurement kind '{mk}'.")
        if mk == "workspace_file" and not (kr.get("measurement_config", {}).get("path") or "").strip():
            raise ValueError(f"Key result #{i+1}: workspace_file requires a path.")
        if mk == "url" and not (kr.get("measurement_config", {}).get("url") or "").strip():
            raise ValueError(f"Key result #{i+1}: url requires a URL.")
        if mk == "formula" and not (kr.get("measurement_config", {}).get("expr") or "").strip():
            raise ValueError(f"Key result #{i+1}: formula requires an expression.")

    # Create the channel first so we can set channel_id on the goal
    base_slug = goal_slug(title)
    slug = await _unique_channel_slug(db, org_id, base_slug)
    channel = Channel(
        org_id=org_id,
        name=title[:120],
        slug=slug,
        description=success_criteria[:500] if success_criteria else description[:500],
        kind="goal",
        created_by_id=author_id,
    )
    db.add(channel)
    await db.flush()

    vis = visibility if visibility in ("private", "team", "org", "viewers") else "team"
    viewer_list = [str(v) for v in (viewer_ids or []) if v]
    goal = Goal(
        org_id=org_id,
        parent_id=parent_id,
        owner_id=owner_id,
        created_by_id=author_id,
        title=title.strip()[:500],
        description=description.strip(),
        success_criteria=success_criteria.strip(),
        state="open",
        deadline=deadline,
        visibility=vis,
        viewer_ids=viewer_list if vis == "viewers" else [],
        channel_id=channel.id,
    )
    db.add(goal)
    await db.flush()

    channel.goal_id = goal.id

    # Members: owner always; author too (so admin creating for someone else can observe)
    db.add(ChannelMember(channel_id=channel.id, person_id=owner_id))
    if author_id != owner_id:
        db.add(ChannelMember(channel_id=channel.id, person_id=author_id))

    for i, kr in enumerate(key_results):
        cfg = kr.get("measurement_config") or {}
        db.add(KeyResult(
            goal_id=goal.id,
            name=(kr.get("name") or "").strip()[:255],
            unit=(kr.get("unit") or "").strip()[:32],
            target_value=_to_float(kr.get("target_value")),
            current_value=_to_float(kr.get("current_value")),
            measurement_kind=(kr.get("measurement_kind") or "manual").strip(),
            measurement_config=cfg,
            sort=i,
        ))

    await db.flush()

    # System event: goal created
    await post_system_event(
        db, channel_id=channel.id, actor_id=author_id,
        event="goal_created",
        summary=f"Goal created: {title}",
        extra={"owner_id": str(owner_id), "visibility": goal.visibility},
    )

    return goal


def _to_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


async def post_system_event(
    db: AsyncSession, *, channel_id: uuid.UUID, actor_id: uuid.UUID | None,
    event: str, summary: str, extra: dict[str, Any] | None = None,
) -> Message:
    msg = Message(
        channel_id=channel_id, person_id=actor_id, is_agent=False,
        kind="system_event", content=summary,
        extra={"event": event, **(extra or {})},
    )
    db.add(msg)
    await db.flush()
    await bus.publish(channel_bus_key(channel_id), "message.new", {
        "id": str(msg.id), "channel_id": str(channel_id),
        "person_id": str(actor_id) if actor_id else None,
        "is_agent": False, "kind": "system_event",
        "content": summary, "extra": msg.extra,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    })
    return msg


async def post_check_in(
    db: AsyncSession, *, goal: Goal, author_id: uuid.UUID, is_agent: bool,
    narrative: str, blockers: list[str] | None = None,
    next_steps: list[str] | None = None, kr_updates: list[dict[str, Any]] | None = None,
) -> Message:
    applied_updates = []
    if kr_updates:
        for upd in kr_updates:
            kr_id = upd.get("kr_id")
            new_val = _to_float(upd.get("value"))
            if not kr_id or new_val is None:
                continue
            try:
                kid = uuid.UUID(kr_id)
            except ValueError:
                continue
            kr = (await db.execute(select(KeyResult).where(KeyResult.id == kid, KeyResult.goal_id == goal.id))).scalar_one_or_none()
            if kr is None:
                continue
            prev = kr.current_value
            kr.current_value = new_val
            kr.last_updated_at = datetime.now(timezone.utc)
            kr.last_updated_by_id = author_id
            kr.last_updated_by_agent = is_agent
            applied_updates.append({
                "kr_id": str(kr.id), "kr_name": kr.name, "unit": kr.unit,
                "from": prev, "to": new_val, "target": kr.target_value,
            })
    payload = {
        "narrative": narrative.strip(),
        "blockers": [b.strip() for b in (blockers or []) if b and b.strip()],
        "next_steps": [n.strip() for n in (next_steps or []) if n and n.strip()],
        "kr_updates": applied_updates,
    }
    msg = Message(
        channel_id=goal.channel_id, person_id=author_id, is_agent=is_agent,
        kind="check_in", content=narrative.strip(), extra=payload,
    )
    db.add(msg)
    await db.flush()
    await bus.publish(channel_bus_key(goal.channel_id), "message.new", {
        "id": str(msg.id), "channel_id": str(goal.channel_id),
        "person_id": str(author_id), "is_agent": is_agent,
        "kind": "check_in", "content": narrative.strip(), "extra": payload,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    })
    return msg


async def post_question(
    db: AsyncSession, *, goal: Goal, author_id: uuid.UUID, is_agent: bool,
    question: str, priority: str = "normal",
) -> Message:
    payload = {"priority": priority if priority in ("blocking", "normal", "fyi") else "normal"}
    msg = Message(
        channel_id=goal.channel_id, person_id=author_id, is_agent=is_agent,
        kind="question", content=question.strip(), extra=payload,
    )
    db.add(msg)
    await db.flush()
    await bus.publish(channel_bus_key(goal.channel_id), "message.new", {
        "id": str(msg.id), "channel_id": str(goal.channel_id),
        "person_id": str(author_id), "is_agent": is_agent,
        "kind": "question", "content": question.strip(), "extra": payload,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    })
    return msg


async def resolve_question(
    db: AsyncSession, *, question: Message, resolver_id: uuid.UUID, is_agent: bool, answer: str,
) -> Message:
    question.resolved_at = datetime.now(timezone.utc)
    question.resolved_by_id = resolver_id
    ans = Message(
        channel_id=question.channel_id, person_id=resolver_id, is_agent=is_agent,
        kind="answer", content=answer.strip(), thread_parent_id=question.id,
        extra={"question_id": str(question.id)},
    )
    db.add(ans)
    await db.flush()
    await bus.publish(channel_bus_key(question.channel_id), "message.new", {
        "id": str(ans.id), "channel_id": str(question.channel_id),
        "person_id": str(resolver_id), "is_agent": is_agent,
        "kind": "answer", "content": answer.strip(), "extra": ans.extra,
        "thread_parent_id": str(question.id),
        "created_at": ans.created_at.isoformat() if ans.created_at else None,
    })
    return ans


async def close_goal(
    db: AsyncSession, *, goal: Goal, actor_id: uuid.UUID, is_agent: bool, note: str = "",
) -> None:
    goal.state = "closed"
    goal.closed_at = datetime.now(timezone.utc)
    goal.closed_by_id = actor_id
    goal.close_note = note.strip()[:2000]
    await post_system_event(
        db, channel_id=goal.channel_id, actor_id=actor_id,
        event="goal_closed",
        summary=f"Goal closed. {note.strip()}" if note.strip() else "Goal closed.",
        extra={"note": note.strip(), "is_agent": is_agent},
    )


async def reopen_goal(
    db: AsyncSession, *, goal: Goal, actor_id: uuid.UUID,
) -> None:
    goal.state = "open"
    goal.closed_at = None
    goal.closed_by_id = None
    goal.close_note = ""
    await post_system_event(
        db, channel_id=goal.channel_id, actor_id=actor_id,
        event="goal_reopened", summary="Goal reopened.",
    )


async def reassign_goal(
    db: AsyncSession, *, goal: Goal, new_owner_id: uuid.UUID, actor_id: uuid.UUID,
) -> None:
    prev_owner = goal.owner_id
    goal.owner_id = new_owner_id
    # Ensure new owner is in the channel
    existing = (
        await db.execute(
            select(ChannelMember).where(
                ChannelMember.channel_id == goal.channel_id,
                ChannelMember.person_id == new_owner_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(ChannelMember(channel_id=goal.channel_id, person_id=new_owner_id))
    await post_system_event(
        db, channel_id=goal.channel_id, actor_id=actor_id,
        event="owner_changed",
        summary="Owner changed.",
        extra={"from": str(prev_owner), "to": str(new_owner_id)},
    )


async def update_kr_value(
    db: AsyncSession, *, kr: KeyResult, new_value: float, actor_id: uuid.UUID, is_agent: bool,
    goal: Goal,
) -> None:
    prev = kr.current_value
    kr.current_value = new_value
    kr.last_updated_at = datetime.now(timezone.utc)
    kr.last_updated_by_id = actor_id
    kr.last_updated_by_agent = is_agent
    await post_system_event(
        db, channel_id=goal.channel_id, actor_id=actor_id,
        event="kr_value_changed",
        summary=f"{kr.name}: {prev if prev is not None else '—'} → {new_value} {kr.unit}".strip(),
        extra={"kr_id": str(kr.id), "from": prev, "to": new_value, "unit": kr.unit, "is_agent": is_agent},
    )


def format_kr_measurement(kr: KeyResult) -> str:
    cfg = kr.measurement_config or {}
    if kr.measurement_kind == "manual":
        return "manual"
    if kr.measurement_kind == "workspace_file":
        return f"file · {cfg.get('path', '?')}"
    if kr.measurement_kind == "url":
        return f"url · {cfg.get('url', '?')[:40]}"
    if kr.measurement_kind == "formula":
        return f"formula · {cfg.get('expr', '?')[:40]}"
    return kr.measurement_kind
