"""Agent permission gates: risky agent actions are queued as AgentAction rows,
require human approval before executing, and are visible in the audit log."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.db.models import AgentAction, Goal, Person
from vynaris.services import goals as gsvc


# Actions that require a human to approve before the agent may execute them.
# Keep this list tight — every gated action is friction for the agent, which
# defeats autonomy. Add only when the action is hard to reverse.
GATED_KINDS = {"close_goal"}


def is_gated(kind: str) -> bool:
    return kind in GATED_KINDS


async def record_pending(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    person_id: uuid.UUID,
    kind: str,
    payload: dict[str, Any],
    rationale: str = "",
    channel_id: uuid.UUID | None = None,
    goal_id: uuid.UUID | None = None,
) -> AgentAction:
    action = AgentAction(
        org_id=org_id, person_id=person_id,
        channel_id=channel_id, goal_id=goal_id,
        kind=kind, payload=payload, rationale=rationale,
        status="pending",
    )
    db.add(action)
    await db.flush()
    return action


async def _load(db: AsyncSession, action_id: uuid.UUID) -> AgentAction | None:
    return (
        await db.execute(select(AgentAction).where(AgentAction.id == action_id))
    ).scalar_one_or_none()


async def can_review(db: AsyncSession, reviewer: Person, action: AgentAction) -> bool:
    if reviewer.org_id != action.org_id:
        return False
    if reviewer.is_admin:
        return True
    # Goal owner may review gates raised by their agent on their goal.
    if action.goal_id is not None:
        g = (await db.execute(select(Goal).where(Goal.id == action.goal_id))).scalar_one_or_none()
        if g is not None and g.owner_id == reviewer.id:
            return True
    return False


async def approve(
    db: AsyncSession, action_id: uuid.UUID, reviewer: Person, note: str = "",
) -> AgentAction | None:
    action = await _load(db, action_id)
    if action is None or action.status != "pending":
        return action
    if not await can_review(db, reviewer, action):
        return None
    action.status = "approved"
    action.reviewed_by_id = reviewer.id
    action.reviewed_at = datetime.now(timezone.utc)
    action.review_note = note.strip()[:2000]
    # execute now
    await _execute(db, action, reviewer=reviewer)
    return action


async def deny(
    db: AsyncSession, action_id: uuid.UUID, reviewer: Person, note: str = "",
) -> AgentAction | None:
    action = await _load(db, action_id)
    if action is None or action.status != "pending":
        return action
    if not await can_review(db, reviewer, action):
        return None
    action.status = "denied"
    action.reviewed_by_id = reviewer.id
    action.reviewed_at = datetime.now(timezone.utc)
    action.review_note = note.strip()[:2000]
    if action.goal_id is not None:
        g = (await db.execute(select(Goal).where(Goal.id == action.goal_id))).scalar_one_or_none()
        if g is not None and g.channel_id is not None:
            await gsvc.post_system_event(
                db, channel_id=g.channel_id, actor_id=reviewer.id,
                event="agent_action_denied",
                summary=f"Denied agent action: {action.kind}",
                extra={"action_id": str(action.id), "kind": action.kind, "note": action.review_note},
            )
    return action


async def _execute(db: AsyncSession, action: AgentAction, reviewer: Person) -> None:
    """Run the underlying operation after approval. Keeps the approval mechanism
    in one place so the tool code can stay simple."""
    if action.kind == "close_goal":
        if action.goal_id is None:
            return
        g = (await db.execute(select(Goal).where(Goal.id == action.goal_id))).scalar_one_or_none()
        if g is None or g.state == "closed":
            return
        note = (action.payload or {}).get("note") or ""
        await gsvc.close_goal(
            db, goal=g, actor_id=action.person_id, is_agent=True, note=str(note)[:2000],
        )
        if g.channel_id is not None:
            await gsvc.post_system_event(
                db, channel_id=g.channel_id, actor_id=reviewer.id,
                event="agent_action_approved",
                summary=f"Approved agent close_goal by {reviewer.name}",
                extra={"action_id": str(action.id), "kind": "close_goal"},
            )
