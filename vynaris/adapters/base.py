"""Adapter contract + status enum. All adapters subclass `Adapter`."""

from __future__ import annotations

import enum
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


class AdapterStatus(str, enum.Enum):
    ENABLED = "enabled"       # env configured and running
    DISABLED = "disabled"     # env missing; treat as coming-soon in UI
    ERRORED = "errored"       # tried to start and failed


@dataclass
class AdapterInfo:
    platform: str
    display_name: str
    icon: str             # emoji or svg name
    status: AdapterStatus
    detail: str = ""      # human-readable reason / connection notes


class Adapter(ABC):
    """One instance per platform. Lifecycled by vynaris.app lifespan."""

    platform: str
    display_name: str
    icon: str = "💬"

    def __init__(self) -> None:
        self.status: AdapterStatus = AdapterStatus.DISABLED
        self.detail: str = ""

    def info(self) -> AdapterInfo:
        return AdapterInfo(
            platform=self.platform,
            display_name=self.display_name,
            icon=self.icon,
            status=self.status,
            detail=self.detail,
        )

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def send(self, external_user_id: str, text: str, extra: dict | None = None) -> None:
        """Send a DM to the bound external user on this platform."""

    async def begin_link(self, person_id: uuid.UUID) -> str:
        """Return a one-time link code and show platform-specific instructions in the UI."""
        from vynaris.services.external_links import generate_link_code
        return await generate_link_code(person_id=person_id, platform=self.platform)
