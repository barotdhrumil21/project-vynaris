# Vynaris

**Enterprise agentic work OS.** Every employee gets a goal-aligned personal agent. Leadership assigns goals. The org sees progress in real time, bounded by hierarchy.

## What it does

- Leadership assigns goals to people
- Each person gets an AI agent bonded to their goals, that can research, analyze data, draft documents, build mini-tools, and update progress
- Leadership sees a live, hierarchical view of what every agent in the org is doing and how goals are tracking
- No integrations with Slack/Teams/etc. — Vynaris is the workspace

## Install (one command)

### macOS / Linux
```bash
./install
```

### Windows (PowerShell)
```powershell
.\install.ps1
```

Then:
```bash
vynaris start
vynaris open   # opens http://localhost:7878
```

First visit walks you through a setup wizard: name your org, add your people, assign their first goals.

## Requirements

- Python 3.11+
- Postgres (the installer sets up a Docker container automatically, or uses your existing local Postgres)
- Anthropic auth — either:
  - an Anthropic API key, **or**
  - the Claude CLI (`npm install -g @anthropic-ai/claude-code` then `claude login`) — uses your Claude subscription

## Architecture

Single Python process:
- FastAPI web server (UI + API + SSE)
- In-process agent runtime (Claude Agent SDK, asyncio)
- APScheduler for scheduled work
- Postgres for structured data
- File-backed workspaces for agent memory and artifacts

Agents follow Nanoclaw-style patterns: markdown skills with progressive disclosure, small sharp tool surface (~10 primitives), plan → act → observe loop, file-based memory.

## Project layout

```
vynaris/
  app.py              FastAPI entrypoint
  config.py           Settings
  db/                 Models, migrations, seed
  web/                Routes + Jinja templates + static
  agent/              Loop, runtime, tools, skill loader
  services/           Visibility, feed, workspace
  cli/                install / start / status / etc.
skills/               Platform skills (markdown)
vynaris-data/         Runtime workspaces + logs (gitignored)
```
