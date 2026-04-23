"""External-channel adapters.

Each adapter binds a platform (Discord, WhatsApp, Teams, …) to Vynaris.
Inbound: platform → `agent_manager.for_person(...).send(text)`.
Outbound: agent runtime → `adapter.send(person, channel, text)`.

Registry is populated at import time; adapters whose env isn't configured
register themselves as stubs so the UI can still list them as "coming soon".
"""

from __future__ import annotations

from vynaris.adapters.base import Adapter, AdapterStatus
from vynaris.adapters.discord_adapter import DiscordAdapter
from vynaris.adapters.gchat_adapter import GChatAdapter
from vynaris.adapters.msteams_adapter import MSTeamsAdapter
from vynaris.adapters.slack_adapter import SlackAdapter
from vynaris.adapters.whatsapp_adapter import WhatsAppAdapter

registry: dict[str, Adapter] = {
    "discord": DiscordAdapter(),
    "whatsapp": WhatsAppAdapter(),
    "msteams": MSTeamsAdapter(),
    "gchat": GChatAdapter(),
    "slack": SlackAdapter(),
}


def get(platform: str) -> Adapter | None:
    return registry.get(platform)


async def start_all() -> None:
    for a in registry.values():
        await a.start()


async def stop_all() -> None:
    for a in registry.values():
        await a.stop()


__all__ = ["Adapter", "AdapterStatus", "registry", "get", "start_all", "stop_all"]
