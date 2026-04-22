"""Vynaris tool primitives — in-process MCP server exposing our tools to the agent."""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any

import httpx
from sqlalchemy import desc, select

from claude_agent_sdk import create_sdk_mcp_server, tool

from vynaris.config import get_settings
from vynaris.db.models import Channel, ChannelMember, Goal, KeyResult, Message, Person
from vynaris.db.session import AsyncSessionLocal
from vynaris.services import goals as gsvc
from vynaris.services.stream_bus import bus, channel_bus_key
from vynaris.services.workspace import safe_relative, workspace_root

settings = get_settings()


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _err(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Error: {msg}"}], "isError": True}


def build_vynaris_tools(person_id: uuid.UUID, org_id: uuid.UUID, default_channel_id: uuid.UUID | None = None) -> Any:
    root = workspace_root(person_id)

    @tool("web_search", "Search the web using DuckDuckGo. Returns titles, URLs, and snippets.", {"query": str, "max_results": int})
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
                    headers={"User-Agent": "Mozilla/5.0 Vynaris/0.2"},
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
                r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 Vynaris/0.2"})
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

    @tool("fs_read", "Read a file from your workspace. Path is relative (e.g. 'memory.md', 'public/report.md').", {"path": str})
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

    @tool("fs_write", "Write to a file in your workspace. Use 'private/...' for private, 'public/...' for visible artifacts.", {"path": str, "content": str})
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

    @tool("fs_list", "List files in a workspace directory. Empty path lists root.", {"path": str})
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

    @tool("code_exec", "Execute a Python snippet in a sandboxed subprocess. cwd is your workspace.", {"code": str, "timeout_sec": int})
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

    @tool("list_channels", "List channels you have access to.", {})
    async def list_channels(args: dict[str, Any]) -> dict[str, Any]:
        async with AsyncSessionLocal() as s:
            me = (await s.execute(select(Person).where(Person.id == person_id))).scalar_one()
            member_rows = (
                await s.execute(select(ChannelMember.channel_id).where(ChannelMember.person_id == me.id))
            ).scalars().all()
            member_set = set(member_rows)
            channels = (
                await s.execute(select(Channel).where(Channel.org_id == me.org_id, Channel.archived == False))
            ).scalars().all()
            visible = [c for c in channels if c.kind == "public" or c.id in member_set or (c.kind == "agent" and c.agent_for_id == me.id)]
        if not visible:
            return _ok("(no channels)")
        lines = ["Channels you can post in:"]
        for c in visible:
            extra = f" goal_id={c.goal_id}" if c.goal_id else ""
            lines.append(f"  - id={c.id} kind={c.kind} name={c.name}{extra}")
        return _ok("\n".join(lines))

    @tool("post_to_channel", "Post a plain message to a channel. If channel_id is omitted, posts to your current channel.", {"channel_id": str, "content": str})
    async def post_to_channel(args: dict[str, Any]) -> dict[str, Any]:
        content = str(args.get("content", "")).strip()
        ch_raw = str(args.get("channel_id", "")).strip()
        if not content:
            return _err("content required")
        target_ch_id: uuid.UUID | None = None
        if ch_raw:
            try:
                target_ch_id = uuid.UUID(ch_raw)
            except ValueError:
                return _err("invalid channel_id")
        else:
            target_ch_id = default_channel_id
        if target_ch_id is None:
            return _err("no channel specified and no default channel set")
        async with AsyncSessionLocal() as s:
            ch = (await s.execute(select(Channel).where(Channel.id == target_ch_id))).scalar_one_or_none()
            me = (await s.execute(select(Person).where(Person.id == person_id))).scalar_one()
            if ch is None or ch.org_id != me.org_id:
                return _err("channel not found")
            if ch.kind == "agent" and ch.agent_for_id != me.id:
                return _err("cannot post to another person's agent channel")
            if ch.kind in ("private", "dm", "goal"):
                member = (
                    await s.execute(
                        select(ChannelMember).where(
                            ChannelMember.channel_id == ch.id, ChannelMember.person_id == me.id
                        )
                    )
                ).scalar_one_or_none()
                if member is None:
                    return _err("you don't have access to that channel")
            msg = Message(
                channel_id=ch.id, person_id=me.id, is_agent=True,
                kind="agent_action", content=content, extra={"source": "post_to_channel"},
            )
            s.add(msg)
            await s.commit()
            await bus.publish(channel_bus_key(ch.id), "message.new", {
                "id": str(msg.id),
                "channel_id": str(ch.id),
                "person_id": str(me.id),
                "is_agent": True,
                "kind": "agent_action",
                "content": content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            })
        return _ok(f"posted to channel {target_ch_id}")

    @tool("view_my_goals", "List goals you (your person) currently own. Returns open + recently closed with KRs.", {})
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
            lines.append(f"  id={g.id}  channel_id={g.channel_id}  visibility={g.visibility}")
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

    @tool("goal_check_in", "Post a structured check-in on a goal. Narrative is required; blockers/next_steps/kr_updates are optional. kr_updates is a list of {kr_id, value}.", {"goal_id": str, "narrative": str, "blockers": list, "next_steps": list, "kr_updates": list})
    async def goal_check_in(args: dict[str, Any]) -> dict[str, Any]:
        narrative = str(args.get("narrative", "")).strip()
        if not narrative:
            return _err("narrative required")
        try:
            gid = uuid.UUID(str(args.get("goal_id", "")))
        except ValueError:
            return _err("invalid goal_id")
        blockers = args.get("blockers") or []
        next_steps = args.get("next_steps") or []
        kr_updates = args.get("kr_updates") or []
        async with AsyncSessionLocal() as s:
            g = (await s.execute(select(Goal).where(Goal.id == gid))).scalar_one_or_none()
            if g is None or g.org_id != org_id or g.channel_id is None:
                return _err("goal not found")
            if g.owner_id != person_id:
                return _err("only the owner's agent can check in on this goal")
            msg = await gsvc.post_check_in(
                s, goal=g, author_id=person_id, is_agent=True,
                narrative=narrative, blockers=blockers, next_steps=next_steps, kr_updates=kr_updates,
            )
            await s.commit()
        return _ok(f"posted check-in ({msg.id}) on goal {gid}")

    @tool("goal_ask", "Raise a clarifying question on a goal. Posts to the goal's channel as an unresolved question.", {"goal_id": str, "content": str, "priority": str})
    async def goal_ask(args: dict[str, Any]) -> dict[str, Any]:
        content = str(args.get("content", "")).strip()
        if not content:
            return _err("content required")
        try:
            gid = uuid.UUID(str(args.get("goal_id", "")))
        except ValueError:
            return _err("invalid goal_id")
        priority = str(args.get("priority", "normal"))
        async with AsyncSessionLocal() as s:
            g = (await s.execute(select(Goal).where(Goal.id == gid))).scalar_one_or_none()
            if g is None or g.org_id != org_id or g.channel_id is None:
                return _err("goal not found")
            msg = await gsvc.post_question(
                s, goal=g, author_id=person_id, is_agent=True,
                question=content, priority=priority,
            )
            await s.commit()
        return _ok(f"asked ({msg.id})")

    @tool("goal_answer", "Answer a previously-raised question. Provide the question's message_id and your answer.", {"message_id": str, "answer": str})
    async def goal_answer(args: dict[str, Any]) -> dict[str, Any]:
        answer = str(args.get("answer", "")).strip()
        if not answer:
            return _err("answer required")
        try:
            mid = uuid.UUID(str(args.get("message_id", "")))
        except ValueError:
            return _err("invalid message_id")
        async with AsyncSessionLocal() as s:
            q = (await s.execute(select(Message).where(Message.id == mid))).scalar_one_or_none()
            if q is None or q.kind != "question" or q.resolved_at is not None:
                return _err("question not found or already resolved")
            await gsvc.resolve_question(s, question=q, resolver_id=person_id, is_agent=True, answer=answer)
            await s.commit()
        return _ok("answered")

    @tool("kr_update", "Update the current value of a key result on one of your goals.", {"kr_id": str, "value": float})
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

    @tool(
        "close_goal",
        "Request to close a goal. This is gated by a PreToolUse hook — a human at /audit reviews and approves. Only call when the success criteria are genuinely met.",
        {"goal_id": str, "note": str},
    )
    async def close_goal(args: dict[str, Any]) -> dict[str, Any]:
        # The SDK PreToolUse hook (see runtime._build_close_goal_gate) intercepts
        # this call, records a pending AgentAction, and returns deny. Control
        # normally never reaches here. If the hook is disabled, fall through to
        # executing the close directly.
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

    return create_sdk_mcp_server(
        name="vynaris", version="0.4.0",
        tools=[
            web_search, web_fetch,
            fs_read, fs_write, fs_list,
            code_exec,
            list_channels, post_to_channel,
            view_my_goals,
            goal_check_in, goal_ask, goal_answer, kr_update, close_goal,
        ],
    )


VYNARIS_TOOL_NAMES = [
    "mcp__vynaris__web_search",
    "mcp__vynaris__web_fetch",
    "mcp__vynaris__fs_read",
    "mcp__vynaris__fs_write",
    "mcp__vynaris__fs_list",
    "mcp__vynaris__code_exec",
    "mcp__vynaris__list_channels",
    "mcp__vynaris__post_to_channel",
    "mcp__vynaris__view_my_goals",
    "mcp__vynaris__goal_check_in",
    "mcp__vynaris__goal_ask",
    "mcp__vynaris__goal_answer",
    "mcp__vynaris__kr_update",
    "mcp__vynaris__close_goal",
]
