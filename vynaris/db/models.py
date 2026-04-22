from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    context: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    people: Mapped[list[Person]] = relationship(back_populates="org", cascade="all, delete-orphan")


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_people_org_email"),
        UniqueConstraint("org_id", "handle", name="uq_people_org_handle"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    # Canonical @handle for this person. Mentioning @handle in a channel fires
    # THEIR agent (not the speaker's). Default = email localpart; admin-editable.
    handle: Mapped[str] = mapped_column(String(32), default="", index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    role_description: Mapped[str] = mapped_column(Text, default="")
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Org hierarchy level (0 = CEO, increasing with depth). level_label is the
    # display string users recognise ("VP", "Director", "IC3", "Partner").
    level: Mapped[int] = mapped_column(Integer, default=5)
    level_label: Mapped[str] = mapped_column(String(48), default="")
    # person_type: employee | external | agent_only. Batch 3.
    person_type: Mapped[str] = mapped_column(String(24), default="employee")
    # working_mode: remote | hybrid | onsite. Batch 3.
    working_mode: Mapped[str] = mapped_column(String(16), default="")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    invite_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    avatar_color: Mapped[str] = mapped_column(String(16), default="#6366f1")
    agent_name: Mapped[str] = mapped_column(String(64), default="")
    agent_emoji: Mapped[str] = mapped_column(String(8), default="🤖")
    agent_identity: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    org: Mapped[Org] = relationship(back_populates="people")
    manager: Mapped[Person | None] = relationship(remote_side="Person.id", foreign_keys=[manager_id])

    @property
    def display_agent_name(self) -> str:
        if (self.agent_name or "").strip():
            return self.agent_name.strip()
        first = (self.name or "").split()[0] if self.name else "Your"
        return f"{first}'s agent"


# ───── Goals + Key Results ─────────────────────────────────────────────────

class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    success_criteria: Mapped[str] = mapped_column(Text, default="")

    # Binary state: open or closed. No progress_pct, no status enum. KRs hold the real numbers.
    state: Mapped[str] = mapped_column(String(16), default="open")  # open | closed
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"), nullable=True
    )
    close_note: Mapped[str] = mapped_column(Text, default="")

    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    # visibility: private | team | org | viewers
    # "viewers" = explicit allow-list in viewer_ids; all other modes ignore it.
    visibility: Mapped[str] = mapped_column(String(16), default="team")
    viewer_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    # 1:1 to its own channel
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class KeyResult(Base):
    __tablename__ = "key_results"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    goal_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(32), default="")  # %, count, $, days, ...
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # how the value gets updated
    measurement_kind: Mapped[str] = mapped_column(String(32), default="manual")  # manual | workspace_file | url
    measurement_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # e.g. {"path": "kpi.csv", "note": "latest row, column default_rate"}
    # or   {"url": "https://...", "note": "JSON $.default_rate"}

    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"), nullable=True
    )
    last_updated_by_agent: Mapped[bool] = mapped_column(Boolean, default=False)

    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GoalWatcher(Base):
    __tablename__ = "goal_watchers"
    __table_args__ = (UniqueConstraint("goal_id", "person_id", name="uq_goal_watchers"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    goal_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_teams_org_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TeamMembership(Base):
    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("team_id", "person_id", name="uq_team_memberships"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    team_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(48), default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ───── Channels + Messages ─────────────────────────────────────────────────

class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_channels_org_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # kind: public | private | dm | agent | goal
    kind: Mapped[str] = mapped_column(String(16), default="public")
    agent_for_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=True, index=True
    )
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True, index=True,  # FK added at goals table layer; avoid circular constraint
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"), nullable=True
    )
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    members: Mapped[list[ChannelMember]] = relationship(back_populates="channel", cascade="all, delete-orphan")


class ChannelMember(Base):
    __tablename__ = "channel_members"
    __table_args__ = (UniqueConstraint("channel_id", "person_id", name="uq_channel_members"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    channel_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    channel: Mapped[Channel] = relationship(back_populates="members")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    channel_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    # kind: text | check_in | question | answer | attachment | system_event | agent_action | goal_update
    kind: Mapped[str] = mapped_column(String(32), default="text")
    content: Mapped[str] = mapped_column(Text, default="")
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    thread_parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # for questions: resolution state
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"), nullable=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    person_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True
    )
    # Skill-driven runs use trigger="skill:<name>"; no DB-side routine table.
    trigger: Mapped[str] = mapped_column(String(48), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ScheduledSkillOverride(Base):
    """Per-org override for a skill's scheduled behaviour.

    Skills carry ``schedule:`` / ``scope:`` in their markdown frontmatter. Orgs
    can disable or reschedule a skill for themselves without editing the file,
    via a row in this table (keyed by skill name).
    """

    __tablename__ = "scheduled_skill_overrides"
    __table_args__ = (UniqueConstraint("org_id", "skill_name", name="uq_scheduled_skill_overrides"),)

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), index=True)
    skill_name: Mapped[str] = mapped_column(String(128), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Optional schedule override (blank = use the skill's frontmatter).
    schedule_cron_override: Mapped[str] = mapped_column(String(64), default="")
    schedule_interval_minutes_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str] = mapped_column(String(32), default="")
    last_run_summary: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class AgentAction(Base):
    """An agent-initiated action that needs human approval before executing.
    Batch 6 permission gate — records risky action requests (close_goal, etc.)."""

    __tablename__ = "agent_actions"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), index=True
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True, index=True
    )
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | approved | denied | expired
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), index=True)
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(48))
    path: Mapped[str] = mapped_column(String(1024))
    public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class SkillRecord(Base):
    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("org_id", "person_id", "name", name="uq_skills_scope_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    path: Mapped[str] = mapped_column(String(1024))
    tier: Mapped[str] = mapped_column(String(16), default="platform")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
