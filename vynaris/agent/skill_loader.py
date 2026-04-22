"""Skill metadata scanner.

Skills live as ``.claude/skills/<name>/SKILL.md``. The Claude Agent SDK
discovers them natively when ``setting_sources=['project']`` and
``skills='all'`` are set — so runtime.py no longer injects skill bodies into
the system prompt, and there's no custom ``load_skill`` tool.

This module still exists because:
  - The /routines view wants a list of skills + their schedule frontmatter.
  - The scheduler needs to register cron/interval jobs from ``schedule:``.
  - Templates want name + description for display.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from vynaris.config import get_settings

settings = get_settings()


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    tier: str            # platform | personal
    path: Path
    schedule_cron: str = ""
    schedule_interval_minutes: int | None = None
    scope: str = ""              # "", per_goal, per_person, one_shot
    fires_only_when: str = ""    # optional predicate (recent_activity_24h|kr_drifting|last_business_day)

    @property
    def is_scheduled(self) -> bool:
        return bool(self.schedule_cron) or (self.schedule_interval_minutes or 0) > 0

    def body(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""


_FRONTMATTER = re.compile(r"^---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)", re.DOTALL)
_KV = re.compile(r"^\s*(?P<k>[A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(?P<v>.+?)\s*$", re.MULTILINE)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = _FRONTMATTER.match(text)
    if not m:
        return {}, text
    meta_raw = m.group("meta")
    body = m.group("body")
    meta = {kv.group("k"): kv.group("v").strip(" \t\"'") for kv in _KV.finditer(meta_raw)}
    return meta, body


def _to_int(v: object) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _load_skills_from(dir_path: Path, tier: str) -> list[Skill]:
    if not dir_path.exists():
        return []
    skills: list[Skill] = []
    for skill_dir in sorted(p for p in dir_path.iterdir() if p.is_dir()):
        md = skill_dir / "SKILL.md"
        if not md.exists():
            continue
        raw = md.read_text(encoding="utf-8")
        meta, _body = parse_frontmatter(raw)
        name = meta.get("name") or skill_dir.name
        desc = meta.get("description") or ""
        skills.append(Skill(
            name=name,
            description=desc,
            tier=tier,
            path=md,
            schedule_cron=meta.get("schedule", "") or "",
            schedule_interval_minutes=_to_int(meta.get("schedule_interval_minutes")),
            scope=meta.get("scope", "") or "",
            fires_only_when=meta.get("fires_only_when", "") or "",
        ))
    return skills


def load_platform_skills() -> list[Skill]:
    return _load_skills_from(settings.skills_dir, "platform")


def load_personal_skills(person_id: str) -> list[Skill]:
    path = settings.workspaces_dir / str(person_id) / "skills"
    return _load_skills_from(path, "personal")


def all_skills_for(person_id: str) -> list[Skill]:
    return load_platform_skills() + load_personal_skills(person_id)


def find_skill(name: str, person_id: str | None = None) -> Skill | None:
    pool = all_skills_for(person_id) if person_id else load_platform_skills()
    for s in pool:
        if s.name == name:
            return s
    return None


def scheduled_skills() -> list[Skill]:
    """Platform skills with a schedule frontmatter — the scheduler's worklist."""
    return [s for s in load_platform_skills() if s.is_scheduled]
