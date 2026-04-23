"""Channel routing — resolve external-platform identity → Vynaris Person.

Thin wrapper so adapters and agent runtime don't duplicate the lookup.
Delegates to ``external_links`` for the authoritative binding row.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from vynaris.services.external_links import Binding, lookup_binding


@dataclass(frozen=True)
class ResolvedEmployee:
    person_id: uuid.UUID
    org_id: uuid.UUID
    channel_id: uuid.UUID


async def resolve_employee(
    *, platform: str, external_user_id: str,
) -> ResolvedEmployee | None:
    """Return the Vynaris employee an inbound external message belongs to."""
    binding: Binding | None = await lookup_binding(
        platform=platform, external_user_id=external_user_id,
    )
    if binding is None:
        return None
    return ResolvedEmployee(
        person_id=binding.person_id,
        org_id=binding.org_id,
        channel_id=binding.channel_id,
    )
