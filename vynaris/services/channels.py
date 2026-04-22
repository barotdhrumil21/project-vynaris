"""Channel helpers: find-or-create DM, get viewer's channels, membership checks."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db.models import Channel, ChannelMember, Person


def slug_from_name(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:80] or f"c-{uuid.uuid4().hex[:6]}"


async def get_viewer_channels(db: AsyncSession, person: Person) -> list[Channel]:
    """All channels the viewer can see: members-in + public + goal channels where
    visibility authorises the viewer (owner / admin / manager-chain / watcher / viewer-list)."""
    member_ids = (
        await db.execute(select(ChannelMember.channel_id).where(ChannelMember.person_id == person.id))
    ).scalars().all()
    member_set = set(member_ids)
    all_channels = (
        await db.execute(
            select(Channel).where(Channel.org_id == person.org_id, Channel.archived == False).order_by(Channel.kind, Channel.name)
        )
    ).scalars().all()

    goal_channels = [c for c in all_channels if c.kind == "goal" and c.id not in member_set]
    if goal_channels:
        from vynaris.db.models import Goal
        from vynaris.services.visibility import can_view_goal
        goals = (
            await db.execute(
                select(Goal).where(Goal.id.in_([c.goal_id for c in goal_channels if c.goal_id]))
            )
        ).scalars().all()
        goals_by_id = {g.id: g for g in goals}
        for c in goal_channels:
            g = goals_by_id.get(c.goal_id)
            if g is not None and await can_view_goal(db, person, g):
                member_set.add(c.id)

    return [c for c in all_channels if c.kind == "public" or c.id in member_set]


async def can_view_channel(db: AsyncSession, person: Person, channel: Channel) -> bool:
    if channel.org_id != person.org_id:
        return False
    if channel.kind == "public":
        return True
    if channel.kind == "agent":
        return channel.agent_for_id == person.id or person.is_admin
    if channel.kind == "goal" and channel.goal_id is not None:
        from vynaris.db.models import Goal
        from vynaris.services.visibility import can_view_goal
        goal = (await db.execute(select(Goal).where(Goal.id == channel.goal_id))).scalar_one_or_none()
        if goal is None:
            return person.is_admin
        return await can_view_goal(db, person, goal)
    member = (
        await db.execute(
            select(ChannelMember).where(
                ChannelMember.channel_id == channel.id,
                ChannelMember.person_id == person.id,
            )
        )
    ).scalar_one_or_none()
    return member is not None or (channel.kind == "private" and person.is_admin)


async def can_post_in(db: AsyncSession, person: Person, channel: Channel) -> bool:
    if channel.kind == "agent":
        return channel.agent_for_id == person.id
    return await can_view_channel(db, person, channel)


async def find_or_create_dm(db: AsyncSession, a: Person, b: Person) -> Channel:
    """1:1 DM channel between two people."""
    ids = sorted([str(a.id), str(b.id)])
    slug = f"dm-{ids[0][:8]}-{ids[1][:8]}"
    existing = (
        await db.execute(select(Channel).where(Channel.org_id == a.org_id, Channel.slug == slug))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    name = f"{a.name} & {b.name}"
    ch = Channel(
        org_id=a.org_id, name=name, slug=slug, kind="dm",
        created_by_id=a.id, description="",
    )
    db.add(ch)
    await db.flush()
    db.add(ChannelMember(channel_id=ch.id, person_id=a.id))
    if a.id != b.id:
        db.add(ChannelMember(channel_id=ch.id, person_id=b.id))
    await db.flush()
    return ch


async def get_or_create_agent_channel(db: AsyncSession, person: Person) -> Channel:
    slug = f"agent-{person.id}"
    existing = (
        await db.execute(select(Channel).where(Channel.org_id == person.org_id, Channel.slug == slug))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    ch = Channel(
        org_id=person.org_id, name="Your agent", slug=slug, kind="agent",
        agent_for_id=person.id, created_by_id=person.id,
        description="Your private workspace with your AI agent.",
    )
    db.add(ch)
    await db.flush()
    db.add(ChannelMember(channel_id=ch.id, person_id=person.id))
    await db.flush()
    return ch


async def dm_counterpart(db: AsyncSession, channel: Channel, viewer: Person) -> Person | None:
    if channel.kind != "dm":
        return None
    members = (
        await db.execute(select(ChannelMember).where(ChannelMember.channel_id == channel.id))
    ).scalars().all()
    for m in members:
        if m.person_id != viewer.id:
            p = (await db.execute(select(Person).where(Person.id == m.person_id))).scalar_one_or_none()
            return p
    return viewer  # DM to self (edge case)
