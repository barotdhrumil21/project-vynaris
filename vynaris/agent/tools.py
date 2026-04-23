"""Vynaris tool primitives — in-process MCP server exposed to the agent.

The toolset is deliberately small (~10). Integrations add conditional tools
only when connected (see `build_integration_tools`).
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any

import httpx
from sqlalchemy import desc, select

from claude_agent_sdk import create_sdk_mcp_server, tool

from vynaris.adapters import registry as adapter_registry
from vynaris.config import get_settings
from vynaris.db.models import Channel, Goal, KeyResult, Message, Person
from vynaris.db.session import AsyncSessionLocal
from vynaris.services import goals as gsvc
from vynaris.services.stream_bus import bus, channel_bus_key
from vynaris.services.workspace import safe_relative, workspace_root

settings = get_settings()


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _err(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Error: {msg}"}], "isError": True}


def build_vynaris_tools(
    person_id: uuid.UUID,
    org_id: uuid.UUID,
    default_channel_id: uuid.UUID | None = None,
    connected_integrations: frozenset[str] = frozenset(),
) -> tuple[Any, list[str]]:
    root = workspace_root(person_id)

    @tool("web_search", "Search the web using DuckDuckGo. Returns titles, URLs, snippets.",
          {"query": str, "max_results": int})
    async def web_search(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        limit = min(int(args.get("max_results", 6) or 6), 10)
        if not query:
            return _err("query is required")
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                r = await client.get(
                    "https://duckduckgo.com/html/",
                    params={"q": query},
                    headers={"User-Agent": "Mozilla/5.0 Vynaris/0.3"},
                )
            html = r.text
            import re
            pattern = re.compile(
                r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.+?)</a>.*?'
                r'<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.+?)</a>',
                re.DOTALL,
            )
            tag_strip = re.compile(r"<[^>]+>")
            results: list[dict[str, str]] = []
            for m in pattern.finditer(html):
                url = m.group("url")
                if url.startswith("//duckduckgo.com/l/?uddg="):
                    from urllib.parse import parse_qs, unquote, urlparse
                    qs = parse_qs(urlparse("https:" + url).query)
                    if "uddg" in qs:
                        url = unquote(qs["uddg"][0])
                results.append({
                    "title": tag_strip.sub("", m.group("title")).strip(),
                    "url": url,
                    "snippet": tag_strip.sub("", m.group("snippet")).strip(),
                })
                if len(results) >= limit:
                    break
            if not results:
                return _ok(f"No results for: {query}")
            lines = [f"Results for: {query}", ""]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet']}")
            return _ok("\n\n".join(lines))
        except Exception as e:
            return _err(f"search failed: {e}")

    @tool("web_fetch", "Fetch a URL and return its text content.", {"url": str})
    async def web_fetch(args: dict[str, Any]) -> dict[str, Any]:
        url = str(args.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            return _err("url must be http(s)://...")
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 Vynaris/0.3"})
            ct = r.headers.get("content-type", "")
            if "application/json" in ct:
                return _ok(r.text[:16000])
            if "text/html" in ct or "<html" in r.text[:1000].lower():
                import re
                t = re.sub(r"<script[\s\S]*?</script>", " ", r.text, flags=re.I)
                t = re.sub(r"<style[\s\S]*?</style>", " ", t, flags=re.I)
                t = re.sub(r"<[^>]+>", " ", t)
                t = re.sub(r"\s+", " ", t).strip()
                return _ok(t[:16000])
            return _ok(r.text[:16000])
        except Exception as e:
            return _err(f"fetch failed: {e}")

    @tool("fs_read", "Read a file from your workspace. Paths are relative.", {"path": str})
    async def fs_read(args: dict[str, Any]) -> dict[str, Any]:
        path = str(args.get("path", "")).strip()
        if not path:
            return _err("path required")
        try:
            target = safe_relative(root, path)
            if not target.exists():
                return _err(f"not found: {path}")
            return _ok(target.read_text(encoding="utf-8"))
        except Exception as e:
            return _err(str(e))

    @tool("fs_write", "Write to a file in your workspace.", {"path": str, "content": str})
    async def fs_write(args: dict[str, Any]) -> dict[str, Any]:
        path = str(args.get("path", "")).strip()
        content = str(args.get("content", ""))
        if not path:
            return _err("path required")
        try:
            target = safe_relative(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return _ok(f"wrote {len(content)} chars to {path}")
        except Exception as e:
            return _err(str(e))

    @tool("fs_list", "List files in a workspace directory. Empty path = root.", {"path": str})
    async def fs_list(args: dict[str, Any]) -> dict[str, Any]:
        path = str(args.get("path", "")).strip() or "."
        try:
            target = safe_relative(root, path)
            if not target.exists():
                return _err(f"not found: {path}")
            items = []
            for p in sorted(target.iterdir()):
                kind = "dir" if p.is_dir() else "file"
                size = p.stat().st_size if p.is_file() else 0
                items.append(f"{kind:4s} {size:>8} {p.name}")
            return _ok("\n".join(items) or "(empty)")
        except Exception as e:
            return _err(str(e))

    @tool("code_exec", "Execute a Python snippet in a sandboxed subprocess. cwd is your workspace.",
          {"code": str, "timeout_sec": int})
    async def code_exec(args: dict[str, Any]) -> dict[str, Any]:
        code = str(args.get("code", ""))
        timeout_sec = min(int(args.get("timeout_sec", 30) or 30), 120)
        if not code:
            return _err("code required")
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(root),
            )
            try:
                out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            except asyncio.TimeoutError:
                proc.kill()
                return _err(f"timed out after {timeout_sec}s")
            out = out_b.decode("utf-8", errors="replace")
            err = err_b.decode("utf-8", errors="replace")
            rc = proc.returncode
            parts = [f"[exit={rc}]"]
            if out:
                parts.append(f"stdout:\n{out[:8000]}")
            if err:
                parts.append(f"stderr:\n{err[:4000]}")
            return _ok("\n\n".join(parts))
        except Exception as e:
            return _err(str(e))

    @tool("reply_to_user",
          "Send a reply to your person on their external-channel DM (Discord, etc). "
          "This is how you respond to them — not by just emitting text.",
          {"content": str})
    async def reply_to_user(args: dict[str, Any]) -> dict[str, Any]:
        content = str(args.get("content", "")).strip()
        if not content:
            return _err("content required")
        if default_channel_id is None:
            return _err("no default channel bound")
        async with AsyncSessionLocal() as s:
            ch = (await s.execute(select(Channel).where(Channel.id == default_channel_id))).scalar_one_or_none()
            if ch is None:
                return _err("channel missing")
            msg = Message(
                channel_id=ch.id, person_id=person_id, is_agent=True,
                kind="text", content=content, extra={"source": "reply_to_user"},
            )
            s.add(msg)
            await s.commit()
            await bus.publish(channel_bus_key(ch.id), "message.new", {
                "id": str(msg.id), "channel_id": str(ch.id),
                "person_id": str(person_id), "is_agent": True,
                "kind": "text", "content": content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            })
            if ch.external_platform and ch.external_user_id:
                adapter = adapter_registry.get(ch.external_platform)
                if adapter is not None:
                    try:
                        await adapter.send(ch.external_user_id, content)
                    except Exception as e:
                        return _err(f"reply saved but platform send failed: {e}")
        return _ok("replied")

    @tool("view_my_goals", "List your open + recently-closed goals with KRs.", {})
    async def view_my_goals(args: dict[str, Any]) -> dict[str, Any]:
        async with AsyncSessionLocal() as s:
            goals = (
                await s.execute(select(Goal).where(Goal.owner_id == person_id).order_by(desc(Goal.updated_at)))
            ).scalars().all()
            if not goals:
                return _ok("(no goals)")
            krs = (
                await s.execute(select(KeyResult).where(KeyResult.goal_id.in_([g.id for g in goals])).order_by(KeyResult.sort))
            ).scalars().all()
        by_goal: dict[uuid.UUID, list[KeyResult]] = {}
        for kr in krs:
            by_goal.setdefault(kr.goal_id, []).append(kr)
        lines = []
        for g in goals:
            lines.append(f"- [{g.state}] {g.title}")
            lines.append(f"  id={g.id}  visibility={g.visibility}")
            if g.deadline:
                lines.append(f"  deadline: {g.deadline}")
            if g.success_criteria:
                lines.append(f"  success: {g.success_criteria}")
            for kr in by_goal.get(g.id, []):
                src = gsvc.format_kr_measurement(kr)
                lines.append(
                    f"    • KR {kr.id} — {kr.name}: "
                    f"{kr.current_value if kr.current_value is not None else '—'} / "
                    f"{kr.target_value if kr.target_value is not None else '?'} {kr.unit or ''}  ({src})"
                )
        return _ok("\n".join(lines))

    @tool("goal_check_in",
          "Post a structured check-in on a goal. Narrative required; other fields optional.",
          {"goal_id": str, "narrative": str, "blockers": list, "next_steps": list, "kr_updates": list})
    async def goal_check_in(args: dict[str, Any]) -> dict[str, Any]:
        narrative = str(args.get("narrative", "")).strip()
        if not narrative:
            return _err("narrative required")
        try:
            gid = uuid.UUID(str(args.get("goal_id", "")))
        except ValueError:
            return _err("invalid goal_id")
        async with AsyncSessionLocal() as s:
            g = (await s.execute(select(Goal).where(Goal.id == gid))).scalar_one_or_none()
            if g is None or g.org_id != org_id or g.channel_id is None:
                return _err("goal not found")
            if g.owner_id != person_id:
                return _err("only the owner's agent can check in")
            msg = await gsvc.post_check_in(
                s, goal=g, author_id=person_id, is_agent=True,
                narrative=narrative,
                blockers=args.get("blockers") or [],
                next_steps=args.get("next_steps") or [],
                kr_updates=args.get("kr_updates") or [],
            )
            await s.commit()
        return _ok(f"posted check-in ({msg.id})")

    @tool("kr_update", "Update the current value of a key result.", {"kr_id": str, "value": float})
    async def kr_update(args: dict[str, Any]) -> dict[str, Any]:
        try:
            kid = uuid.UUID(str(args.get("kr_id", "")))
        except ValueError:
            return _err("invalid kr_id")
        try:
            value = float(args.get("value"))
        except (TypeError, ValueError):
            return _err("value must be a number")
        async with AsyncSessionLocal() as s:
            kr = (await s.execute(select(KeyResult).where(KeyResult.id == kid))).scalar_one_or_none()
            if kr is None:
                return _err("kr not found")
            g = (await s.execute(select(Goal).where(Goal.id == kr.goal_id))).scalar_one_or_none()
            if g is None or g.org_id != org_id or g.owner_id != person_id:
                return _err("not your goal")
            await gsvc.update_kr_value(s, kr=kr, new_value=value, actor_id=person_id, is_agent=True, goal=g)
            await s.commit()
        return _ok(f"updated KR {kid} to {value}")

    @tool("close_goal",
          "Request to close a goal. Gated — a human approves in /audit.",
          {"goal_id": str, "note": str})
    async def close_goal(args: dict[str, Any]) -> dict[str, Any]:
        try:
            gid = uuid.UUID(str(args.get("goal_id", "")))
        except ValueError:
            return _err("invalid goal_id")
        note = str(args.get("note", "")).strip()
        async with AsyncSessionLocal() as s:
            g = (await s.execute(select(Goal).where(Goal.id == gid))).scalar_one_or_none()
            if g is None or g.org_id != org_id:
                return _err("goal not found")
            if g.owner_id != person_id:
                return _err("only the owner's agent can close")
            await gsvc.close_goal(s, goal=g, actor_id=person_id, is_agent=True, note=note)
            await s.commit()
        return _ok(f"closed goal {gid}")

    base_tools = [
        web_search, web_fetch,
        fs_read, fs_write, fs_list,
        code_exec,
        reply_to_user,
        view_my_goals,
        goal_check_in, kr_update, close_goal,
    ]

    from vynaris.agent.data_tools import build_data_tools
    from vynaris.agent.integration_tools import build_integration_tools

    data_tools, data_names = build_data_tools(person_id=person_id, org_id=org_id)
    int_tools, int_names = build_integration_tools(
        person_id=person_id, org_id=org_id, connected=connected_integrations,
    )

    return create_sdk_mcp_server(
        name="vynaris", version="0.5.0", tools=base_tools + data_tools + int_tools,
    ), data_names + int_names


VYNARIS_CORE_TOOL_NAMES = [
    "mcp__vynaris__web_search",
    "mcp__vynaris__web_fetch",
    "mcp__vynaris__fs_read",
    "mcp__vynaris__fs_write",
    "mcp__vynaris__fs_list",
    "mcp__vynaris__code_exec",
    "mcp__vynaris__reply_to_user",
    "mcp__vynaris__view_my_goals",
    "mcp__vynaris__goal_check_in",
    "mcp__vynaris__kr_update",
    "mcp__vynaris__close_goal",
]
