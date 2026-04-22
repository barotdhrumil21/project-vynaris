"""Onboarding helpers: shared person creation, bulk CSV import, demo-org packs.

Batch 2 wires the CSV import + level fields; Batch 4 plugs per-persona pack
content into ``install_persona_pack``.
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.auth import new_invite_token
from vynaris.db.models import Channel, ChannelMember, Person
from vynaris.db.seed import AVATAR_COLORS


PERSON_TYPES = ("employee", "external", "agent_only")
WORKING_MODES = ("", "remote", "hybrid", "onsite")

HANDLE_RE = re.compile(r"[^a-z0-9-]")


def _normalize_handle(s: str) -> str:
    s = HANDLE_RE.sub("-", (s or "").lower()).strip("-")
    return s[:32] or ""


async def pick_handle(db: AsyncSession, org_id: uuid.UUID, name: str, email: str) -> str:
    """Pick a unique @handle for a new person in the given org.

    Preference order: first-name slug → first+last-initial → email localpart → localpart-N.
    """
    first = (name or "").split()[0] if name else ""
    last = (name or "").split()[-1] if len((name or "").split()) > 1 else ""
    localpart = (email or "").split("@", 1)[0]
    candidates: list[str] = []
    if first:
        candidates.append(_normalize_handle(first))
    if first and last:
        candidates.append(_normalize_handle(f"{first}-{last[:1]}"))
    if localpart:
        candidates.append(_normalize_handle(localpart))
    # filter empties and dedupe preserving order
    seen = set()
    ordered = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)
    for cand in ordered:
        taken = (
            await db.execute(
                select(Person.id).where(Person.org_id == org_id, Person.handle == cand)
            )
        ).first()
        if taken is None:
            return cand
    # fall back: append digits
    base = ordered[-1] if ordered else "user"
    n = 2
    while True:
        candidate = f"{base}-{n}"[:32]
        taken = (
            await db.execute(
                select(Person.id).where(Person.org_id == org_id, Person.handle == candidate)
            )
        ).first()
        if taken is None:
            return candidate
        n += 1
        if n > 999:
            return f"{base[:24]}-{uuid.uuid4().hex[:6]}"


@dataclass
class PersonDraft:
    name: str
    email: str
    title: str = ""
    level: int = 5
    level_label: str = ""
    manager_email: str = ""
    role_description: str = ""
    person_type: str = "employee"
    working_mode: str = ""
    is_admin: bool = False


@dataclass
class BulkImportResult:
    created: list[Person] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (email, reason)
    errors: list[tuple[int, str]] = field(default_factory=list)  # (row_index, message)

    @property
    def created_count(self) -> int:
        return len(self.created)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def _avatar_color(existing_count: int) -> str:
    return AVATAR_COLORS[existing_count % len(AVATAR_COLORS)]


async def _existing_people_in_org(db: AsyncSession, org_id: uuid.UUID) -> dict[str, Person]:
    rows = (await db.execute(select(Person).where(Person.org_id == org_id))).scalars().all()
    return {p.email.lower(): p for p in rows}


async def create_person(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    draft: PersonDraft,
    manager_id: uuid.UUID | None = None,
    existing_count: int | None = None,
    with_agent_channel: bool = True,
    add_to_general: bool = True,
) -> Person:
    if existing_count is None:
        existing_count = len(
            (await db.execute(select(Person).where(Person.org_id == org_id))).scalars().all()
        )
    email = draft.email.strip().lower()
    if not email:
        raise ValueError("email is required")
    if not draft.name.strip():
        raise ValueError("name is required")

    ptype = draft.person_type if draft.person_type in PERSON_TYPES else "employee"
    wmode = draft.working_mode if draft.working_mode in WORKING_MODES else ""

    level = draft.level
    try:
        level = int(level)
    except (TypeError, ValueError):
        level = 5
    level = max(0, min(10, level))

    handle = await pick_handle(db, org_id, draft.name, email)

    p = Person(
        org_id=org_id,
        name=draft.name.strip()[:255],
        email=email[:255],
        handle=handle,
        title=draft.title.strip()[:255],
        role_description=draft.role_description.strip(),
        manager_id=manager_id,
        level=level,
        level_label=draft.level_label.strip()[:48],
        person_type=ptype,
        working_mode=wmode,
        is_admin=bool(draft.is_admin),
        invite_token=new_invite_token(),
        avatar_color=_avatar_color(existing_count),
    )
    db.add(p)
    await db.flush()

    if add_to_general:
        general = (
            await db.execute(
                select(Channel).where(Channel.org_id == org_id, Channel.slug == "general")
            )
        ).scalar_one_or_none()
        if general is not None:
            db.add(ChannelMember(channel_id=general.id, person_id=p.id))

    if with_agent_channel and ptype != "agent_only":
        agent_ch = Channel(
            org_id=org_id,
            name="Your agent",
            slug=f"agent-{p.id}",
            kind="agent",
            agent_for_id=p.id,
            created_by_id=p.id,
            description="Your private workspace with your AI agent.",
        )
        db.add(agent_ch)
        await db.flush()
        db.add(ChannelMember(channel_id=agent_ch.id, person_id=p.id))

    return p


async def bulk_import_people(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    csv_text: str,
    default_send_invite: bool = True,
) -> BulkImportResult:
    """Parse a CSV and create people. Columns (header row required):
        name, email, title, level, level_label, manager_email,
        role_description, person_type, working_mode, make_admin

    Rows are applied in two passes so manager_email can reference a person
    created earlier in the same import.
    """
    result = BulkImportResult()
    reader = csv.DictReader(io.StringIO(csv_text))
    rows: list[dict[str, str]] = [{k.strip().lower(): (v or "").strip() for k, v in r.items()} for r in reader]

    existing = await _existing_people_in_org(db, org_id)
    existing_count = len(existing)

    # ── pass 1: create people without manager link (record intended manager)
    intended_mgr: dict[str, str] = {}  # email -> manager_email
    for idx, row in enumerate(rows, start=2):  # +2: header is row 1
        email = (row.get("email") or "").lower()
        if not email:
            if any(row.values()):  # ignore fully empty rows
                result.errors.append((idx, "missing email"))
            continue
        if email in existing:
            result.skipped.append((email, "already exists"))
            continue
        draft = PersonDraft(
            name=row.get("name", ""),
            email=email,
            title=row.get("title", ""),
            level=_to_int(row.get("level"), 5),
            level_label=row.get("level_label", ""),
            manager_email=(row.get("manager_email") or "").lower(),
            role_description=row.get("role_description", ""),
            person_type=row.get("person_type", "employee") or "employee",
            working_mode=row.get("working_mode", ""),
            is_admin=_truthy(row.get("make_admin")),
        )
        try:
            p = await create_person(
                db, org_id=org_id, draft=draft,
                existing_count=existing_count,
                manager_id=None,  # resolved in pass 2
            )
        except Exception as e:
            result.errors.append((idx, str(e)))
            continue
        existing[email] = p
        existing_count += 1
        if draft.manager_email:
            intended_mgr[email] = draft.manager_email
        result.created.append(p)

    # ── pass 2: link managers
    await db.flush()
    for email, mgr_email in intended_mgr.items():
        person = existing.get(email)
        manager = existing.get(mgr_email)
        if person is None or manager is None:
            if person is not None and manager is None:
                result.errors.append((0, f"{email}: manager {mgr_email} not found"))
            continue
        person.manager_id = manager.id

    return result


def _to_int(v: Any, default: int) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def _truthy(v: Any) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "y", "x"}


# ── persona packs (Batch 4 fills these in) ────────────────────────────────────

PERSONA_PACKS = {
    "sanghavi": {
        "label": "Sanghavi (Trading / Credit Risk)",
        "blurb": "LC discrepancy drafts, EDPMS reconciliation, per-buyer MIS.",
    },
    "schafer": {
        "label": "Schäfer (Manufacturing)",
        "blurb": "8D drafts, OEE analysis, shift handovers, Ausbildung rotation.",
    },
    "barrett": {
        "label": "Barrett (Law firm)",
        "blurb": "Time-entry drafting, precedent search, Chambers submissions.",
    },
    "nimbus": {
        "label": "Nimbus (SaaS GTM)",
        "blurb": "Forecast prep, deal reviews, pipeline drift, QBR preparation.",
    },
    "luma": {
        "label": "Luma (DTC)",
        "blurb": "Performance weekly, creative briefs, attribution reconciliation.",
    },
}


async def install_persona_pack(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    admin: Person,
    pack: str,
) -> dict[str, Any]:
    """Install a persona pack into the org. Implementation lives in
    vynaris/services/persona_packs.py (Batch 4); this is the dispatcher.
    """
    from vynaris.services.persona_packs import install
    return await install(db, org_id=org_id, admin=admin, pack=pack)
