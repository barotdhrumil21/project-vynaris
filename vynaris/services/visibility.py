"""Hierarchical visibility for goals + people.

Semantics (top-down, not symmetric):
- admin                       → everything
- owner                       → their own goal
- watcher                     → goals they explicitly watch
- private                     → owner + admin + watchers only
- team                        → owner + admin + watchers + manager chain up + teammates
- org                         → everyone in the org
- viewers (explicit list)     → owner + admin + watchers + ids in goal.viewer_ids
- person_type == "external"   → only goals where they are a watcher OR listed in viewer_ids
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db.models import Goal, GoalWatcher, Person, TeamMembership


async def transitive_reports(db: AsyncSession, manager_id: uuid.UUID) -> set[uuid.UUID]:
    seen: set[uuid.UUID] = set()
    frontier = {manager_id}
    while frontier:
        rows = (
            await db.execute(
                select(Person.id).where(Person.manager_id.in_(frontier))
            )
        ).scalars().all()
        new = set(rows) - seen - {manager_id}
        if not new:
            break
        seen |= new
        frontier = new
    return seen


async def _is_watcher(db: AsyncSession, goal_id: uuid.UUID, person_id: uuid.UUID) -> bool:
    row = (
        await db.execute(
            select(GoalWatcher.id).where(
                GoalWatcher.goal_id == goal_id,
                GoalWatcher.person_id == person_id,
            )
        )
    ).scalar_one_or_none()
    return row is not None


async def _shared_team(db: AsyncSession, a: uuid.UUID, b: uuid.UUID) -> bool:
    a_teams = set(
        (await db.execute(select(TeamMembership.team_id).where(TeamMembership.person_id == a))).scalars().all()
    )
    if not a_teams:
        return False
    b_teams = set(
        (await db.execute(select(TeamMembership.team_id).where(TeamMembership.person_id == b))).scalars().all()
    )
    return bool(a_teams & b_teams)


async def can_view_goal(db: AsyncSession, viewer: Person, goal: Goal) -> bool:
    if viewer.is_admin:
        return True
    if goal.owner_id == viewer.id:
        return True
    if await _is_watcher(db, goal.id, viewer.id):
        return True

    if viewer.person_type == "external":
        # Externals only see goals where they are explicit viewers or watchers.
        if goal.visibility == "viewers" and str(viewer.id) in (goal.viewer_ids or []):
            return True
        return False

    if goal.visibility == "org":
        return True

    if goal.visibility == "viewers":
        return str(viewer.id) in (goal.viewer_ids or [])

    if goal.visibility == "private":
        return False  # owner/admin/watcher already handled above

    # "team" (default) — manager chain + teammates
    reports = await transitive_reports(db, viewer.id)
    if goal.owner_id in reports:
        return True
    if await _shared_team(db, viewer.id, goal.owner_id):
        return True
    return False


async def can_view_person(db: AsyncSession, viewer: Person, target_id: uuid.UUID) -> bool:
    if viewer.is_admin:
        return True
    if viewer.id == target_id:
        return True
    reports = await transitive_reports(db, viewer.id)
    return target_id in reports
