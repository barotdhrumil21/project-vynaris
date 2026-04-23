"""WhatsApp adapter — stub. UI lists it as coming soon."""

from __future__ import annotations

from vynaris.adapters.base import Adapter, AdapterStatus


class WhatsAppAdapter(Adapter):
    platform = "whatsapp"
    display_name = "WhatsApp"
    icon = "📱"

    async def start(self) -> None:
        self.status = AdapterStatus.DISABLED
        self.detail = "WhatsApp Cloud API adapter — on the roadmap."

    async def stop(self) -> None:
        return

    async def send(self, external_user_id: str, text: str, extra: dict | None = None) -> None:
        raise NotImplementedError("WhatsApp adapter is not enabled in this build.")
