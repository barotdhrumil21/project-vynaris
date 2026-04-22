"""Scheduled skills.

The Claude Agent SDK's native primitive is the Skill (markdown + frontmatter in
``.claude/skills/``). We schedule them by reading ``schedule:`` / ``scope:`` /
``fires_only_when:`` from each skill's frontmatter — no DB-side Routine table.

Per-org overrides (disable, reschedule) live in ``scheduled_skill_overrides``.
"""

from __future__ import annotations

import calendar
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.agent.runtime import manager as agent_manager
from vynaris.agent.skill_loader import Skill, load_platform_skills, scheduled_skills
from vynaris.db.models import (
    AgentRun, Channel, Goal, KeyResult, Org, Person, ScheduledSkillOverride,
)
from vynaris.db.session import AsyncSessionLocal

log = logging.getLogger("vynaris.scheduled_skills")


# ── effective schedule (skill frontmatter merged with per-org override) ────────


@dataclass(frozen=True)
class EffectiveSchedule:
    skill: Skill
    org_id: uuid.UUID
    enabled: bool
    schedule_cron: str
    schedule_interval_minutes: int | None
    scope: str
    fires_only_when: str
    last_run_at: datetime | None
    last_run_status: str
    last_run_summary: str


async def _overrides_by_skill(db: AsyncSession, org_id: uuid.UUID) -> dict[str, ScheduledSkillOverride]:
    rows = (
        await db.execute(
            select(ScheduledSkillOverride).where(ScheduledSkillOverride.org_id == org_id)
        )
    ).scalars().all()
    return {r.skill_name: r for r in rows}


async def effective_schedules_for_org(
    db: AsyncSession, org_id: uuid.UUID,
) -> list[EffectiveSchedule]:
    skills = scheduled_skills()
    overrides = await _overrides_by_skill(db, org_id)
    out: list[EffectiveSchedule] = []
    for s in skills:
        ov = overrides.get(s.name)
        enabled = True if ov is None else ov.enabled
        cron = s.schedule_cron
        interval = s.schedule_interval_minutes
        if ov is not None:
            if ov.schedule_cron_override:
                cron = ov.schedule_cron_override
            if ov.schedule_interval_minutes_override:
                interval = ov.schedule_interval_minutes_override
        out.append(EffectiveSchedule(
            skill=s,
            org_id=org_id,
            enabled=enabled,
            schedule_cron=cron,
            schedule_interval_minutes=interval,
            scope=s.scope or "per_goal",
            fires_only_when=s.fires_only_when or "",
            last_run_at=ov.last_run_at if ov else None,
            last_run_status=ov.last_run_status if ov else "",
            last_run_summary=ov.last_run_summary if ov else "",
        ))
    return out


async def all_effective_schedules() -> list[EffectiveSchedule]:
    """Used by the scheduler to register jobs across every org."""
    out: list[EffectiveSchedule] = []
    async with AsyncSessionLocal() as db:
        orgs = (await db.execute(select(Org))).scalars().all()
        for org in orgs:
            out.extend(await effective_schedules_for_org(db, org.id))
    return out


# ── ensure override row exists so we have a landing spot for last_run + toggle ─


async def ensure_override(
    db: AsyncSession, *, org_id: uuid.UUID, skill_name: str,
) -> ScheduledSkillOverride:
    existing = (
        await db.execute(
            select(ScheduledSkillOverride).where(
                ScheduledSkillOverride.org_id == org_id,
                ScheduledSkillOverride.skill_name == skill_name,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    row = ScheduledSkillOverride(org_id=org_id, skill_name=skill_name, enabled=True)
    db.add(row)
    await db.flush()
    return row


async def toggle_override(
    db: AsyncSession, *, org_id: uuid.UUID, skill_name: str,
) -> ScheduledSkillOverride:
    row = await ensure_override(db, org_id=org_id, skill_name=skill_name)
    row.enabled = not row.enabled
    await db.flush()
    return row


async def set_schedule_override(
    db: AsyncSession, *, org_id: uuid.UUID, skill_name: str,
    cron: str | None = None, interval_minutes: int | None = None,
) -> ScheduledSkillOverride:
    row = await ensure_override(db, org_id=org_id, skill_name=skill_name)
    if cron is not None:
        row.schedule_cron_override = cron.strip()[:64]
    if interval_minutes is not None:
        row.schedule_interval_minutes_override = (
            interval_minutes if interval_minutes > 0 else None
        )
    await db.flush()
    return row


# ── firing ────────────────────────────────────────────────────────────────────


def _build_prompt(skill: Skill, *, goal: Goal | None) -> str:
    parts = [f"[scheduled skill: {skill.name}]"]
    parts.append(
        f"A scheduled skill has fired. Use the `{skill.name}` skill to carry out this run."
    )
    if goal is not None:
        parts.append(f"Context: goal_id={goal.id}, channel_id={goal.channel_id}, title={goal.title!r}.")
    parts.append(
        "Follow the skill's instructions. Post via `goal_check_in` / `post_to_channel` as it directs. "
        "Keep it short if nothing material is there to say."
    )
    return "\n\n".join(parts)


async def _active_person(p: Person) -> bool:
    if p.person_type == "agent_only":
        return True
    return bool(p.password_hash)


async def _recent_activity(db: AsyncSession, channel_id: uuid.UUID, hours: int) -> bool:
    from vynaris.db.models import Message
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    m = (
        await db.execute(
            select(Message)
            .where(Message.channel_id == channel_id, Message.created_at >= cutoff)
            .limit(1)
        )
    ).scalar_one_or_none()
    return m is not None


def _is_last_business_day() -> bool:
    today = datetime.now(timezone.utc).date()
    last = calendar.monthrange(today.year, today.month)[1]
    target = last
    while target > 0:
        candidate = today.replace(day=target)
        if candidate.weekday() < 5:
            break
        target -= 1
    return today.day == target


def _kr_is_drifting(kr: KeyResult) -> bool:
    cfg = kr.measurement_config or {}
    raw = cfg.get("drift_threshold_pct")
    if raw is None:
        return False
    try:
        th = abs(float(raw)) / 100.0
    except (TypeError, ValueError):
        return False
    if th == 0 or kr.current_value is None or kr.target_value is None or kr.target_value == 0:
        return False
    return abs(kr.current_value - kr.target_value) / abs(kr.target_value) >= th


async def _fire_one(
    db: AsyncSession, *, skill: Skill, person: Person, goal: Goal | None,
    channel_id: uuid.UUID,
) -> None:
    marker = AgentRun(
        person_id=person.id,
        channel_id=channel_id,
        trigger=f"skill:{skill.name}",
        status="queued",
        started_at=datetime.now(timezone.utc),
    )
    db.add(marker)
    await db.flush()
    try:
        agent = await agent_manager.for_person(person.id, person.org_id, channel_id=channel_id)
        await agent.send(_build_prompt(skill, goal=goal))
        marker.status = "dispatched"
    except Exception as e:
        marker.status = "failed"
        marker.summary = str(e)
        log.exception("skill %s: dispatch failed for %s: %s", skill.name, person.email, e)


async def _agent_channel_for(db: AsyncSession, person: Person) -> Channel | None:
    slug = f"agent-{person.id}"
    return (
        await db.execute(
            select(Channel).where(Channel.org_id == person.org_id, Channel.slug == slug)
        )
    ).scalar_one_or_none()


async def fire_skill(
    skill_name: str, *, org_id: uuid.UUID, only_target_goal_id: uuid.UUID | None = None,
) -> dict[str, int]:
    """Fire a scheduled skill for one org. Iterates targets per scope."""
    from vynaris.agent.skill_loader import find_skill
    skill = find_skill(skill_name)
    if skill is None:
        return {"fired": 0, "reason": "skill-not-found"}

    async with AsyncSessionLocal() as db:
        override = (
            await db.execute(
                select(ScheduledSkillOverride).where(
                    ScheduledSkillOverride.org_id == org_id,
                    ScheduledSkillOverride.skill_name == skill_name,
                )
            )
        ).scalar_one_or_none()
        if override is not None and not override.enabled:
            return {"fired": 0, "reason": "disabled"}

        gate = skill.fires_only_when
        if gate == "last_business_day" and not _is_last_business_day():
            await _record_run(db, override, org_id, skill_name, status="skipped", summary="not last business day")
            return {"fired": 0, "reason": "not-last-business-day"}

        fired = 0
        scope = skill.scope or "per_goal"
        if scope == "per_goal":
            goals_q = select(Goal).where(
                Goal.org_id == org_id, Goal.state == "open", Goal.channel_id.is_not(None),
            )
            if only_target_goal_id is not None:
                goals_q = goals_q.where(Goal.id == only_target_goal_id)
            goals = (await db.execute(goals_q)).scalars().all()
            for g in goals:
                if gate == "recent_activity_24h" and not await _recent_activity(db, g.channel_id, 24):
                    continue
                if gate == "kr_drifting":
                    krs = (
                        await db.execute(select(KeyResult).where(KeyResult.goal_id == g.id))
                    ).scalars().all()
                    if not any(_kr_is_drifting(k) for k in krs):
                        continue
                owner = (await db.execute(select(Person).where(Person.id == g.owner_id))).scalar_one_or_none()
                if owner is None or not await _active_person(owner):
                    continue
                await _fire_one(db, skill=skill, person=owner, goal=g, channel_id=g.channel_id)
                fired += 1

        elif scope == "per_person":
            people = (
                await db.execute(select(Person).where(Person.org_id == org_id))
            ).scalars().all()
            for p in people:
                if not await _active_person(p):
                    continue
                ch = await _agent_channel_for(db, p)
                if ch is None:
                    continue
                await _fire_one(db, skill=skill, person=p, goal=None, channel_id=ch.id)
                fired += 1

        await _record_run(
            db, override, org_id, skill_name,
            status="ok" if fired > 0 else "no-op",
            summary=f"fired {fired} agent run(s)",
        )
        await db.commit()
        return {"fired": fired}


async def _record_run(
    db: AsyncSession,
    override: ScheduledSkillOverride | None,
    org_id: uuid.UUID,
    skill_name: str,
    *,
    status: str,
    summary: str,
) -> None:
    if override is None:
        override = await ensure_override(db, org_id=org_id, skill_name=skill_name)
    override.last_run_at = datetime.now(timezone.utc)
    override.last_run_status = status[:32]
    override.last_run_summary = summary[:2000]


# ── run-history helpers ────────────────────────────────────────────────────────


async def recent_runs_for_skill(
    db: AsyncSession, skill_name: str, org_id: uuid.UUID, limit: int = 30,
) -> list[AgentRun]:
    trigger = f"skill:{skill_name}"
    # filter by org via the owning person
    rows = (
        await db.execute(
            select(AgentRun)
            .join(Person, Person.id == AgentRun.person_id)
            .where(AgentRun.trigger == trigger, Person.org_id == org_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)
