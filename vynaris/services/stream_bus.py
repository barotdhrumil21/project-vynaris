"""In-process pub/sub for streaming agent + message events to SSE subscribers."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from typing import Any


class StreamBus:
    def __init__(self) -> None:
        self._channels: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)

    def subscribe(self, channel: str) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=512)
        self._channels[channel].add(q)
        return q

    def unsubscribe(self, channel: str, q: asyncio.Queue[str]) -> None:
        self._channels[channel].discard(q)
        if not self._channels[channel]:
            self._channels.pop(channel, None)

    async def publish(self, channel: str, event: str, data: dict[str, Any]) -> None:
        payload = json.dumps({"event": event, "data": data}, default=str)
        dead: list[asyncio.Queue[str]] = []
        for q in list(self._channels.get(channel, ())):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(channel, q)


bus = StreamBus()


def channel_bus_key(channel_id: uuid.UUID | str) -> str:
    return f"channel:{channel_id}"


def person_inbox_key(person_id: uuid.UUID | str) -> str:
    return f"inbox:{person_id}"
