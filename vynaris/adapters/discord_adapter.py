"""Discord adapter — the only real external channel for the demo.

Boot: if DISCORD_BOT_TOKEN is set, connects a discord.py client, listens for
DMs and `/link <code>` commands. Otherwise registers as DISABLED.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from vynaris.adapters.base import Adapter, AdapterStatus
from vynaris.config import get_settings

log = logging.getLogger(__name__)


class DiscordAdapter(Adapter):
    platform = "discord"
    display_name = "Discord"
    icon = "💬"

    def __init__(self) -> None:
        super().__init__()
        self._client: Any = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        token = get_settings().discord_bot_token.strip()
        if not token:
            self.status = AdapterStatus.DISABLED
            self.detail = "Set DISCORD_BOT_TOKEN in .env to enable Discord."
            return
        try:
            import discord  # type: ignore
        except ImportError:
            self.status = AdapterStatus.DISABLED
            self.detail = "Install `discord.py` to enable Discord."
            return

        intents = discord.Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        client = discord.Client(intents=intents)
        self._client = client

        @client.event
        async def on_ready() -> None:
            log.info("discord adapter ready as %s", client.user)

        @client.event
        async def on_message(message: Any) -> None:
            if message.author.bot:
                return
            # DM only for the demo. Server channels can come later.
            if getattr(message.channel, "type", None) and str(message.channel.type) != "private":
                return
            await self._on_dm(
                external_user_id=str(message.author.id),
                external_handle=str(message.author.name),
                text=message.content or "",
            )

        async def runner() -> None:
            try:
                await client.start(token)
            except Exception as e:
                log.exception("discord client crashed")
                self.status = AdapterStatus.ERRORED
                self.detail = str(e)

        self._task = asyncio.create_task(runner(), name="discord-adapter")
        self.status = AdapterStatus.ENABLED
        self.detail = "Connecting…"

    async def stop(self) -> None:
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
        if self._task is not None:
            self._task.cancel()

    async def send(self, external_user_id: str, text: str, extra: dict | None = None) -> None:
        if self._client is None or self.status != AdapterStatus.ENABLED:
            log.warning("discord.send skipped — adapter not enabled")
            return
        try:
            user = await self._client.fetch_user(int(external_user_id))
            for chunk in _chunks(text, 1900):
                await user.send(chunk)
        except Exception:
            log.exception("discord.send failed")

    async def _on_dm(self, *, external_user_id: str, external_handle: str, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        if text.lower().startswith("/link "):
            code = text.split(None, 1)[1].strip()
            await self._handle_link(external_user_id=external_user_id, external_handle=external_handle, code=code)
            return
        await self._dispatch_to_agent(external_user_id=external_user_id, text=text)

    async def _handle_link(self, *, external_user_id: str, external_handle: str, code: str) -> None:
        from vynaris.services.external_links import verify_link_code
        result = await verify_link_code(
            platform=self.platform,
            code=code,
            external_user_id=external_user_id,
            external_handle=external_handle,
        )
        if result.ok:
            await self.send(external_user_id, f"Linked as {result.person_name} @ {result.org_name}. Try: *what's on my plate?*")
        else:
            await self.send(external_user_id, f"Link failed: {result.error}")

    async def _dispatch_to_agent(self, *, external_user_id: str, text: str) -> None:
        from vynaris.agent.runtime import manager as agent_manager
        from vynaris.services.external_links import lookup_binding
        binding = await lookup_binding(platform=self.platform, external_user_id=external_user_id)
        if binding is None:
            await self.send(
                external_user_id,
                "Not linked yet. Generate a code in Vynaris → Channels → Connect Discord, "
                "then DM me `/link YOURCODE`.",
            )
            return
        agent = await agent_manager.for_person(
            binding.person_id, binding.org_id, channel_id=binding.channel_id,
        )
        await agent.send(text)


def _chunks(s: str, n: int) -> list[str]:
    return [s[i:i + n] for i in range(0, max(len(s), 1), n)] or [""]
