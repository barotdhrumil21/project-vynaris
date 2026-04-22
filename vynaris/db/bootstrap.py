"""Idempotent schema bootstrap + in-place migration for goal v2."""

from __future__ import annotations

import logging

from sqlalchemy import text

from vynaris.db.models import Base
from vynaris.db.session import engine

logger = logging.getLogger(__name__)


async def create_all() -> None:
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.run_sync(Base.metadata.create_all)
        await _upgrade_schema(conn)


async def drop_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _upgrade_schema(conn) -> None:
    """Additive migrations for v2+ goal model. Safe to run repeatedly."""
    statements = [
        # goals: add new columns; drop legacy status/progress_pct if still present
        "ALTER TABLE goals ADD COLUMN IF NOT EXISTS state VARCHAR(16) DEFAULT 'open'",
        "ALTER TABLE goals ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ",
        "ALTER TABLE goals ADD COLUMN IF NOT EXISTS closed_by_id UUID REFERENCES people(id) ON DELETE SET NULL",
        "ALTER TABLE goals ADD COLUMN IF NOT EXISTS close_note TEXT DEFAULT ''",
        "ALTER TABLE goals ADD COLUMN IF NOT EXISTS channel_id UUID REFERENCES channels(id) ON DELETE SET NULL",
        "ALTER TABLE goals ADD COLUMN IF NOT EXISTS created_by_id UUID REFERENCES people(id) ON DELETE SET NULL",
        # Backfill created_by_id from channel.created_by_id for pre-existing goals
        "UPDATE goals g SET created_by_id = c.created_by_id FROM channels c WHERE g.created_by_id IS NULL AND g.channel_id = c.id AND c.created_by_id IS NOT NULL",
        # messages: add resolution fields
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ",
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS resolved_by_id UUID REFERENCES people(id) ON DELETE SET NULL",
        # channels: goal_id backref
        "ALTER TABLE channels ADD COLUMN IF NOT EXISTS goal_id UUID",
        # agent personalization
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS agent_name VARCHAR(64) DEFAULT ''",
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS agent_emoji VARCHAR(8) DEFAULT '🤖'",
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS agent_identity TEXT DEFAULT ''",
        # Batch 2: org hierarchy level
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS level INT DEFAULT 5",
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS level_label VARCHAR(48) DEFAULT ''",
        # Batch 3: person taxonomy
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS person_type VARCHAR(24) DEFAULT 'employee'",
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS working_mode VARCHAR(16) DEFAULT ''",
        # Batch 3: goal viewer list (explicit person ids for private+list visibility)
        "ALTER TABLE goals ADD COLUMN IF NOT EXISTS viewer_ids JSONB DEFAULT '[]'::jsonb",
        # Batch 6: agent_actions table is created by SQLAlchemy create_all — no ALTER needed.
        # Routine pivot — the Routine ORM table was replaced with skill-frontmatter
        # scheduling. Drop the column + table if they exist from the earlier shape.
        "ALTER TABLE agent_runs DROP COLUMN IF EXISTS routine_id",
        "DROP TABLE IF EXISTS routines CASCADE",
        # Canonical @handle per person — unique within org. Backfill from email localpart.
        "ALTER TABLE people ADD COLUMN IF NOT EXISTS handle VARCHAR(32) DEFAULT ''",
        "UPDATE people SET handle = lower(regexp_replace(split_part(email, '@', 1), '[^a-z0-9]+', '-', 'g')) WHERE coalesce(handle, '') = ''",
        # drop legacy columns (safe if they don't exist)
        "ALTER TABLE goals DROP COLUMN IF EXISTS status",
        "ALTER TABLE goals DROP COLUMN IF EXISTS progress_pct",
        # drop legacy goal_updates table — superseded by messages with kind=check_in
        "DROP TABLE IF EXISTS goal_updates CASCADE",
        # any legacy goals without a channel_id become immediately closed (they're from before the redesign)
        "UPDATE goals SET state = 'closed', closed_at = NOW() WHERE channel_id IS NULL AND (state IS NULL OR state = 'open')",
    ]
    for stmt in statements:
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            logger.warning("migration step failed (continuing): %s — %s", stmt[:80], e)
