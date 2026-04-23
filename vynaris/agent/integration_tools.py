"""Integration-backed tools — added to the agent only when the integration is connected."""

from __future__ import annotations

import uuid
from typing import Any

from claude_agent_sdk import tool


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _err(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Error: {msg}"}], "isError": True}


def build_integration_tools(
    *, person_id: uuid.UUID, org_id: uuid.UUID, connected: frozenset[str],
) -> tuple[list[Any], list[str]]:
    tools: list[Any] = []
    names: list[str] = []

    if "gmail" in connected:
        from vynaris.integrations import gmail as gmail_svc

        @tool("gmail_search",
              "Search your person's Gmail inbox. Returns recent matching threads.",
              {"query": str, "max_results": int})
        async def gmail_search(args: dict[str, Any]) -> dict[str, Any]:
            q = str(args.get("query", "")).strip()
            limit = min(int(args.get("max_results", 10) or 10), 25)
            if not q:
                return _err("query required")
            try:
                out = await gmail_svc.search(org_id=org_id, query=q, max_results=limit)
                return _ok(out)
            except Exception as e:
                return _err(str(e))

        @tool("gmail_send",
              "Send an email via your person's Gmail account. Ask before sending anything non-trivial.",
              {"to": str, "subject": str, "body": str})
        async def gmail_send(args: dict[str, Any]) -> dict[str, Any]:
            to = str(args.get("to", "")).strip()
            subject = str(args.get("subject", "")).strip()
            body = str(args.get("body", "")).strip()
            if not (to and subject and body):
                return _err("to, subject, body are all required")
            try:
                out = await gmail_svc.send(org_id=org_id, to=to, subject=subject, body=body)
                return _ok(out)
            except Exception as e:
                return _err(str(e))

        tools.extend([gmail_search, gmail_send])
        names.extend(["mcp__vynaris__gmail_search", "mcp__vynaris__gmail_send"])

    return tools, names
