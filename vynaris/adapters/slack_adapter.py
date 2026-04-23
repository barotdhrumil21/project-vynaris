"""Slack adapter — stub."""

from __future__ import annotations

from vynaris.adapters.base import Adapter, AdapterStatus


class SlackAdapter(Adapter):
    platform = "slack"
    display_name = "Slack"
    icon = "🟣"

    async def start(self) -> None:
        self.status = AdapterStatus.DISABLED
        self.detail = "Slack adapter — on the roadmap."

    async def stop(self) -> None:
        return

    async def send(self, external_user_id: str, text: str, extra: dict | None = None) -> None:
        raise NotImplementedError("Slack adapter is not enabled in this build.")
