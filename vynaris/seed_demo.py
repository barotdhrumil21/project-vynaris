"""Seed scripts for demos. Currently: Credit Risk flow from build plan Demo 1."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from vynaris.db.models import Goal, KeyResult, Person
from vynaris.db.session import AsyncSessionLocal
from vynaris.services.goals import create_goal
from vynaris.services.workspace import ensure_workspace


CSV_CONTENT = """date,default_rate,new_customer_approval_rate,policy_updates_shipped
2026-01-31,3.4,61,0
2026-02-07,3.5,62,0
2026-02-14,3.5,62,1
2026-02-21,3.6,63,1
2026-02-28,3.6,62,1
2026-03-07,3.5,62,1
2026-03-14,3.6,61,1
2026-03-21,3.7,61,1
2026-03-28,3.7,62,1
2026-04-04,3.8,62,1
2026-04-11,3.8,62,1
2026-04-18,3.9,62,1
"""


async def seed_credit_risk_demo(email: str, console: Any) -> None:
    async with AsyncSessionLocal() as s:
        owner = (await s.execute(select(Person).where(Person.email == email))).scalar_one_or_none()
        if owner is None:
            console.print(f"[red]✗[/red] no user with email {email}")
            return

        # Seed workspace + CSV
        root = ensure_workspace(owner.id)
        public = root / "public"
        public.mkdir(parents=True, exist_ok=True)
        csv_path = public / "kpi.csv"
        csv_path.write_text(CSV_CONTENT, encoding="utf-8")
        console.print(f"[green]✓[/green] wrote {csv_path}")

        # Avoid duplicate seed
        existing = (
            await s.execute(
                select(Goal).where(
                    Goal.org_id == owner.org_id,
                    Goal.owner_id == owner.id,
                    Goal.title.like("Reduce default rate%"),
                )
            )
        ).scalars().first()
        if existing is not None:
            console.print(f"[yellow]![/yellow] demo goal already exists: {existing.id}")
            console.print(f"  channel: /c/{existing.channel_id}")
            return

        # workspace_file KRs leave current_value unset; the first scheduler tick
        # (or manual refresh) reads the CSV and populates the real value.
        krs = [
            {
                "name": "Default rate (sub-50L, 90-day rolling)",
                "unit": "%",
                "target_value": 3.2,
                "measurement_kind": "workspace_file",
                "measurement_config": {
                    "path": "public/kpi.csv",
                    "column": "default_rate",
                    "alias": "default_rate",
                    "cadence_minutes": 1440,
                    "note": "latest row, column default_rate",
                },
            },
            {
                "name": "New-customer approval rate",
                "unit": "%",
                "target_value": 65,
                "measurement_kind": "workspace_file",
                "measurement_config": {
                    "path": "public/kpi.csv",
                    "column": "new_customer_approval_rate",
                    "alias": "approval",
                    "cadence_minutes": 1440,
                },
            },
            {
                "name": "Policy updates shipped",
                "unit": "count",
                "target_value": 2,
                "current_value": 1,
                "measurement_kind": "manual",
                "measurement_config": {"alias": "policies"},
            },
        ]
        goal = await create_goal(
            s,
            org_id=owner.org_id,
            owner_id=owner.id,
            author_id=owner.id,
            title="Reduce default rate on sub-50L SMB book to under 3.2% by end of Q3",
            description="Credit risk demo goal — Sanghavi persona, Batch 1.",
            success_criteria="Default rate under 3.2% (90-day rolling) with approval rate ≥65%.",
            deadline=date.today() + timedelta(days=60),
            visibility="team",
            key_results=krs,
        )
        await s.commit()
        console.print(f"[green]✓[/green] created goal {goal.id}")
        console.print(f"  channel: /c/{goal.channel_id}")
        console.print()
        console.print("  Now: start Vynaris, open the goal channel, click ↻ on the default-rate KR.")
