"""Microsoft Teams adapter — stub."""

from __future__ import annotations

from vynaris.adapters.base import Adapter, AdapterStatus


class MSTeamsAdapter(Adapter):
    platform = "msteams"
    display_name = "Microsoft Teams"
    icon = "🔷"

    async def start(self) -> None:
        self.status = AdapterStatus.DISABLED
        self.detail = "Microsoft Teams Bot Framework adapter — on the roadmap."

    async def stop(self) -> None:
        return

    async def send(self, external_user_id: str, text: str, extra: dict | None = None) -> None:
        raise NotImplementedError("MS Teams adapter is not enabled in this build.")
