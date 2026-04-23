"""Google Chat adapter — stub."""

from __future__ import annotations

from vynaris.adapters.base import Adapter, AdapterStatus


class GChatAdapter(Adapter):
    platform = "gchat"
    display_name = "Google Chat"
    icon = "🟢"

    async def start(self) -> None:
        self.status = AdapterStatus.DISABLED
        self.detail = "Google Chat adapter — on the roadmap."

    async def stop(self) -> None:
        return

    async def send(self, external_user_id: str, text: str, extra: dict | None = None) -> None:
        raise NotImplementedError("Google Chat adapter is not enabled in this build.")
