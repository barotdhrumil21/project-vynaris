"""Per-person agent runtime. Bound to a specific channel for responses."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookContext,
    HookMatcher,
    PreToolUseHookInput,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from vynaris.agent.system_prompt import build_system_prompt
from vynaris.agent.tools import VYNARIS_TOOL_NAMES, build_vynaris_tools
from vynaris.services import gates as gate_svc
from vynaris.config import get_settings
from vynaris.db.models import AgentRun, Goal, Message, Org, Person
from vynaris.db.session import AsyncSessionLocal
from vynaris.services.stream_bus import bus, channel_bus_key
from vynaris.services.workspace import ensure_workspace

log = logging.getLogger(__name__)
settings = get_settings()


async def _build_prompt_context(person_id: uuid.UUID) -> dict[str, Any]:
    async with AsyncSessionLocal() as s:
        person = (await s.execute(select(Person).where(Person.id == person_id))).scalar_one()
        org = (await s.execute(select(Org).where(Org.id == person.org_id))).scalar_one()
        goals = (
            await s.execute(
                select(Goal).where(Goal.owner_id == person.id, Goal.state == "open").order_by(desc(Goal.updated_at))
            )
        ).scalars().all()
        from vynaris.db.models import KeyResult, Message
        krs_by_goal: dict[uuid.UUID, list[KeyResult]] = {}
        if goals:
            all_krs = (
                await s.execute(
                    select(KeyResult).where(KeyResult.goal_id.in_([g.id for g in goals])).order_by(KeyResult.sort)
                )
            ).scalars().all()
            for kr in all_krs:
                krs_by_goal.setdefault(kr.goal_id, []).append(kr)

        recent_events_by_channel: dict[uuid.UUID, list[Message]] = {}
        channel_ids = [g.channel_id for g in goals if g.channel_id is not None]
        if channel_ids:
            recent = (
                await s.execute(
                    select(Message)
                    .where(Message.channel_id.in_(channel_ids))
                    .order_by(desc(Message.created_at))
                    .limit(200)
                )
            ).scalars().all()
            for m in recent:
                recent_events_by_channel.setdefault(m.channel_id, []).append(m)

    goals_lines = []
    for g in goals:
        goals_lines.append(f"- [open] {g.title}")
        goals_lines.append(f"  goal_id: {g.id}    channel_id: {g.channel_id}")
        if g.deadline:
            goals_lines.append(f"  deadline: {g.deadline}")
        if g.success_criteria:
            goals_lines.append(f"  success: {g.success_criteria}")
        for kr in krs_by_goal.get(g.id, []):
            goals_lines.append(
                f"    • kr_id={kr.id} — {kr.name}: "
                f"{kr.current_value if kr.current_value is not None else '—'} / "
                f"{kr.target_value if kr.target_value is not None else '?'} {kr.unit or ''}".rstrip()
            )
    goals_text = "\n".join(goals_lines) or "(no goals assigned yet)"

    event_lines = []
    for g in goals:
        if g.channel_id is None:
            continue
        msgs = list(reversed(recent_events_by_channel.get(g.channel_id, [])))[-6:]
        if not msgs:
            continue
        event_lines.append(f"- Goal: {g.title}")
        for m in msgs:
            who = "agent" if m.is_agent else "person"
            body_preview = (m.content or "")[:200].replace("\n", " ")
            event_lines.append(f"    · [{m.kind} by {who}] {body_preview}")
    recent_goal_events_text = "\n".join(event_lines) or "(no recent goal events)"

    return {
        "person": person,
        "org": org,
        "goals_text": goals_text,
        "recent_goal_events_text": recent_goal_events_text,
    }


def _build_close_goal_gate(
    person_id: uuid.UUID, org_id: uuid.UUID, default_channel_id: uuid.UUID,
):
    """Factory: returns a PreToolUse hook bound to this agent's person.

    When the agent tries `mcp__vynaris__close_goal`, record a pending AgentAction
    and return `permissionDecision: "deny"` with a reason. A human reviews at
    /audit and approves there — which runs the actual close.
    """
    async def hook(
        input_data: PreToolUseHookInput,
        matcher: str | None,
        context: HookContext,
    ) -> dict[str, Any]:
        args = input_data.get("tool_input") or {}
        gid_raw = str(args.get("goal_id", "")).strip()
        note = str(args.get("note", "")).strip()
        try:
            gid = uuid.UUID(gid_raw)
        except (TypeError, ValueError):
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "invalid goal_id for close_goal",
                }
            }
        async with AsyncSessionLocal() as s:
            g = (await s.execute(select(Goal).where(Goal.id == gid))).scalar_one_or_none()
            if g is None or g.org_id != org_id:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "goal not found",
                    }
                }
            channel_id_for_action = g.channel_id or default_channel_id
            action = await gate_svc.record_pending(
                s,
                org_id=org_id,
                person_id=person_id,
                kind="close_goal",
                payload={"goal_id": str(gid), "note": note},
                rationale=note,
                channel_id=channel_id_for_action,
                goal_id=g.id,
            )
            # Post a visible system event so the goal channel reflects the pending action.
            from vynaris.services import goals as gsvc
            if g.channel_id is not None:
                await gsvc.post_system_event(
                    s,
                    channel_id=g.channel_id,
                    actor_id=None,
                    event="agent_action_pending",
                    summary=f"Agent requested close_goal (awaiting approval): {note[:120]}",
                    extra={
                        "action_id": str(action.id),
                        "kind": "close_goal",
                        "is_agent": True,
                    },
                )
            await s.commit()
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"gated: close_goal request {action.id} is awaiting human approval. "
                    f"The owner or an admin will review it in /audit."
                ),
            }
        }

    return hook


class PersonAgent:
    def __init__(self, person_id: uuid.UUID, org_id: uuid.UUID, channel_id: uuid.UUID) -> None:
        self.person_id = person_id
        self.org_id = org_id
        self.channel_id = channel_id
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name=f"agent-{self.person_id}")

    async def stop(self) -> None:
        self._stop.set()
        await self.queue.put("__STOP__")
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                self._task.cancel()

    async def send(self, text: str) -> None:
        self.start()
        await self.queue.put(text)

    async def _run(self) -> None:
        try:
            ensure_workspace(self.person_id)
            ctx = await _build_prompt_context(self.person_id)
            person: Person = ctx["person"]
            org: Org = ctx["org"]
            root = ensure_workspace(self.person_id)

            system_prompt = build_system_prompt(
                person_name=person.name,
                person_title=person.title,
                person_role=person.role_description,
                org_name=org.name,
                org_context=org.context,
                goals_text=ctx["goals_text"],
                recent_goal_events_text=ctx["recent_goal_events_text"],
                workspace_dir=str(root),
                default_channel_id=str(self.channel_id),
                agent_name=person.display_agent_name,
                agent_identity=person.agent_identity or "",
            )

            mcp_server = build_vynaris_tools(self.person_id, self.org_id, default_channel_id=self.channel_id)

            gate_hook = _build_close_goal_gate(self.person_id, self.org_id, self.channel_id)

            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                mcp_servers={"vynaris": mcp_server},
                allowed_tools=[
                    *VYNARIS_TOOL_NAMES,
                    "Read", "Write", "Edit", "Grep", "Glob",
                ],
                permission_mode="bypassPermissions",
                cwd=str(root),
                model=settings.vynaris_model,
                # Load .claude/skills/ and CLAUDE.md from project root — the SDK
                # handles skill discovery natively; we don't inject bodies ourselves.
                setting_sources=["project"],
                skills="all",
                hooks={
                    "PreToolUse": [
                        HookMatcher(
                            matcher="mcp__vynaris__close_goal",
                            hooks=[gate_hook],
                        ),
                    ],
                },
                include_partial_messages=True,
            )

            async with ClaudeSDKClient(options=options) as client:
                while not self._stop.is_set():
                    try:
                        text = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    if text == "__STOP__":
                        break

                    run_id = await self._start_run()
                    try:
                        await client.query(text)
                        await self._consume_response(client, run_id)
                        await self._end_run(run_id, "completed")
                    except Exception as e:
                        log.exception("agent run failed")
                        await self._publish_error(str(e))
                        await self._end_run(run_id, "failed", summary=str(e))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("agent runtime crashed: %s", e)
            await self._publish_error(f"runtime: {e}")

    async def _consume_response(self, client: ClaudeSDKClient, run_id: uuid.UUID) -> None:
        assistant_block_buf: list[dict[str, Any]] = []
        collected_texts: list[str] = []

        async def flush_text_message(final: bool = False) -> None:
            if not collected_texts:
                return
            combined = "\n\n".join(t for t in collected_texts if t.strip())
            if not combined.strip():
                return
            async with AsyncSessionLocal() as s:
                msg = Message(
                    channel_id=self.channel_id,
                    person_id=self.person_id,
                    is_agent=True,
                    kind="text",
                    content=combined,
                    run_id=run_id,
                    extra={"blocks": list(assistant_block_buf)},
                )
                s.add(msg)
                await s.commit()
                await s.refresh(msg)
                await bus.publish(channel_bus_key(self.channel_id), "message.new", {
                    "id": str(msg.id),
                    "channel_id": str(self.channel_id),
                    "person_id": str(self.person_id),
                    "is_agent": True,
                    "kind": "text",
                    "content": combined,
                    "extra": msg.extra,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                })
            collected_texts.clear()

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        collected_texts.append(block.text)
                        assistant_block_buf.append({"type": "text", "text": block.text})
                        await self._publish_event("message.stream_text", {"text": block.text, "run_id": str(run_id)})
                    elif isinstance(block, ThinkingBlock):
                        assistant_block_buf.append({"type": "thinking", "text": block.thinking})
                        await self._publish_event("message.thinking", {"text": block.thinking})
                    elif isinstance(block, ToolUseBlock):
                        assistant_block_buf.append({
                            "type": "tool_use", "id": block.id,
                            "name": block.name, "input": block.input,
                        })
                        await self._publish_event("tool.use", {
                            "id": block.id, "name": block.name, "input": block.input,
                        })
                    elif isinstance(block, ToolResultBlock):
                        content = block.content
                        text = ""
                        if isinstance(content, str):
                            text = content
                        elif isinstance(content, list):
                            text = "\n".join(
                                c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
                            )
                        assistant_block_buf.append({
                            "type": "tool_result", "tool_use_id": block.tool_use_id,
                            "text": text[:4000], "is_error": bool(block.is_error),
                        })
                        await self._publish_event("tool.result", {
                            "tool_use_id": block.tool_use_id,
                            "text": text[:4000], "is_error": bool(block.is_error),
                        })
            elif isinstance(msg, UserMessage):
                for block in msg.content:
                    if isinstance(block, ToolResultBlock):
                        content = block.content
                        text = ""
                        if isinstance(content, str):
                            text = content
                        elif isinstance(content, list):
                            text = "\n".join(
                                c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
                            )
                        assistant_block_buf.append({
                            "type": "tool_result", "tool_use_id": block.tool_use_id,
                            "text": text[:4000], "is_error": bool(block.is_error),
                        })
                        await self._publish_event("tool.result", {
                            "tool_use_id": block.tool_use_id,
                            "text": text[:4000], "is_error": bool(block.is_error),
                        })
            elif isinstance(msg, ResultMessage):
                await flush_text_message(final=True)
                await self._publish_event("message.done", {
                    "turns": getattr(msg, "num_turns", None),
                    "total_cost_usd": getattr(msg, "total_cost_usd", None),
                })
                break

        await flush_text_message(final=True)

    async def _start_run(self) -> uuid.UUID:
        async with AsyncSessionLocal() as s:
            run = AgentRun(
                person_id=self.person_id, channel_id=self.channel_id,
                trigger="user_message", status="running",
                started_at=datetime.now(timezone.utc),
            )
            s.add(run)
            await s.commit()
            await s.refresh(run)
            return run.id

    async def _end_run(self, run_id: uuid.UUID, status: str, summary: str | None = None) -> None:
        async with AsyncSessionLocal() as s:
            run = (await s.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one_or_none()
            if run is not None:
                run.status = status
                run.finished_at = datetime.now(timezone.utc)
                if summary:
                    run.summary = summary
                await s.commit()

    async def _publish_event(self, event: str, data: dict[str, Any]) -> None:
        await bus.publish(channel_bus_key(self.channel_id), event, data)

    async def _publish_error(self, message: str) -> None:
        await bus.publish(channel_bus_key(self.channel_id), "agent.error", {"message": message})


class AgentManager:
    def __init__(self) -> None:
        self._agents: dict[tuple[uuid.UUID, uuid.UUID], PersonAgent] = {}
        self._lock = asyncio.Lock()

    async def for_person(self, person_id: uuid.UUID, org_id: uuid.UUID, channel_id: uuid.UUID) -> PersonAgent:
        key = (person_id, channel_id)
        async with self._lock:
            agent = self._agents.get(key)
            if agent is None:
                agent = PersonAgent(person_id, org_id, channel_id)
                self._agents[key] = agent
                agent.start()
            return agent

    async def shutdown(self) -> None:
        async with self._lock:
            agents = list(self._agents.values())
            self._agents.clear()
        for a in agents:
            await a.stop()


manager = AgentManager()
