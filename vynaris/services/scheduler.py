"""In-process APScheduler.

- ``kr_refresh``: fixed interval job (every 5 minutes).
- ``skill:<org_id>:<skill_name>``: one job per (org × scheduled skill) — the
  skill's frontmatter carries ``schedule:`` and ``scope:``; per-org overrides
  in ``scheduled_skill_overrides`` can disable or reschedule.
"""

from __future__ import annotations

import logging
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

log = logging.getLogger("vynaris.scheduler")

_scheduler: AsyncIOScheduler | None = None


# ── fixed jobs ────────────────────────────────────────────────────────────────


async def _kr_refresh_tick() -> None:
    from vynaris.services.kr_refresh import refresh_all_due
    try:
        stats = await refresh_all_due()
        if stats["attempted"]:
            log.info("kr refresh: attempted=%d changed=%d", stats["attempted"], stats["changed"])
    except Exception as e:
        log.exception("kr refresh tick failed: %s", e)


# ── skill jobs ────────────────────────────────────────────────────────────────


async def _skill_tick(org_id_str: str, skill_name: str) -> None:
    from vynaris.services.scheduled_skills import fire_skill
    try:
        oid = uuid.UUID(org_id_str)
    except (TypeError, ValueError):
        log.warning("skill tick: invalid org id %r", org_id_str)
        return
    try:
        stats = await fire_skill(skill_name, org_id=oid)
        if stats.get("fired"):
            log.info("skill %s (%s): fired %d", skill_name, org_id_str, stats["fired"])
    except Exception as e:
        log.exception("skill %s tick failed: %s", skill_name, e)


def _trigger_for_effective(eff) -> CronTrigger | IntervalTrigger | None:
    if eff.schedule_cron.strip():
        try:
            return CronTrigger.from_crontab(eff.schedule_cron.strip())
        except Exception as e:
            log.warning("skill %s: invalid cron %r: %s", eff.skill.name, eff.schedule_cron, e)
            return None
    if eff.schedule_interval_minutes and eff.schedule_interval_minutes > 0:
        return IntervalTrigger(minutes=int(eff.schedule_interval_minutes))
    return None


def _job_id(org_id: uuid.UUID, skill_name: str) -> str:
    return f"skill:{org_id}:{skill_name}"


async def reload_skill_jobs() -> int:
    """Drop all skill:* jobs and re-register from current (org × skill) schedules."""
    sched = _scheduler
    if sched is None:
        return 0
    for job in list(sched.get_jobs()):
        if job.id.startswith("skill:"):
            try:
                sched.remove_job(job.id)
            except Exception:
                pass
    from vynaris.services.scheduled_skills import all_effective_schedules
    schedules = await all_effective_schedules()
    registered = 0
    for eff in schedules:
        if not eff.enabled:
            continue
        trig = _trigger_for_effective(eff)
        if trig is None:
            continue
        sched.add_job(
            _skill_tick,
            args=[str(eff.org_id), eff.skill.name],
            trigger=trig,
            id=_job_id(eff.org_id, eff.skill.name),
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=600,
        )
        registered += 1
    log.info("scheduled-skill jobs registered: %d", registered)
    return registered


async def on_schedule_changed(org_id: uuid.UUID, skill_name: str) -> None:
    """Called by CRUD routes after an override changes."""
    await reload_skill_jobs()


# ── lifecycle ─────────────────────────────────────────────────────────────────


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(
        _kr_refresh_tick,
        trigger=IntervalTrigger(minutes=5),
        id="kr_refresh",
        replace_existing=True,
        max_instances=1, coalesce=True, misfire_grace_time=300,
    )
    sched.start()
    _scheduler = sched
    log.info("scheduler started (kr_refresh every 5m); skill jobs loaded from frontmatter next")
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler
