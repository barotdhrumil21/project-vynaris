"""Gmail integration — OAuth flow + search + send.

Config stored in Integration.config_encrypted as:
    {"refresh_token": "...", "email": "user@example.com", "scopes": [...]}

Access tokens are minted per-call using the refresh token; not cached.
"""

from __future__ import annotations

import base64
import logging
import uuid
from email.message import EmailMessage
from typing import Any

import httpx

from vynaris.config import get_settings
from vynaris.services import integrations as isvc

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"
API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def is_configured() -> bool:
    s = get_settings()
    return bool(s.gmail_client_id and s.gmail_client_secret and s.gmail_redirect_uri)


def auth_url(state: str) -> str:
    s = get_settings()
    params = {
        "client_id": s.gmail_client_id,
        "redirect_uri": s.gmail_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    from urllib.parse import urlencode
    return f"{AUTH_URI}?{urlencode(params)}"


async def exchange_code(code: str) -> dict[str, Any]:
    s = get_settings()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(TOKEN_URI, data={
            "code": code,
            "client_id": s.gmail_client_id,
            "client_secret": s.gmail_client_secret,
            "redirect_uri": s.gmail_redirect_uri,
            "grant_type": "authorization_code",
        })
        r.raise_for_status()
        tokens = r.json()
        # fetch email for display
        info = await client.get(USERINFO_URI, headers={"Authorization": f"Bearer {tokens['access_token']}"})
        info.raise_for_status()
        email = info.json().get("email", "")
    return {"refresh_token": tokens.get("refresh_token", ""), "email": email, "scopes": SCOPES}


async def _access_token(refresh_token: str) -> str:
    s = get_settings()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(TOKEN_URI, data={
            "refresh_token": refresh_token,
            "client_id": s.gmail_client_id,
            "client_secret": s.gmail_client_secret,
            "grant_type": "refresh_token",
        })
        r.raise_for_status()
        return r.json()["access_token"]


async def _load_config(org_id: uuid.UUID) -> dict[str, Any]:
    row = await isvc.get(org_id, "gmail")
    if row is None or row.status != "connected":
        raise RuntimeError("Gmail is not connected for this org.")
    cfg = isvc.decrypt_config(row.config_encrypted)
    if not cfg.get("refresh_token"):
        raise RuntimeError("Gmail config missing refresh_token — reconnect.")
    return cfg


async def search(*, org_id: uuid.UUID, query: str, max_results: int = 10) -> str:
    cfg = await _load_config(org_id)
    token = await _access_token(cfg["refresh_token"])
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{API_BASE}/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "maxResults": max_results},
        )
        r.raise_for_status()
        ids = [m["id"] for m in (r.json().get("messages") or [])]
        if not ids:
            return f"No matching messages for: {query}"
        lines = [f"Found {len(ids)} matching messages for: {query}", ""]
        for mid in ids[:max_results]:
            m = await client.get(
                f"{API_BASE}/messages/{mid}",
                headers={"Authorization": f"Bearer {token}"},
                params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
            )
            m.raise_for_status()
            data = m.json()
            headers = {h["name"]: h["value"] for h in (data.get("payload", {}).get("headers") or [])}
            lines.append(f"- {headers.get('Date', '?')}  |  {headers.get('From', '?')}")
            lines.append(f"  {headers.get('Subject', '(no subject)')}")
            if data.get("snippet"):
                lines.append(f"  {data['snippet'][:200]}")
        return "\n".join(lines)


async def send(*, org_id: uuid.UUID, to: str, subject: str, body: str) -> str:
    cfg = await _load_config(org_id)
    token = await _access_token(cfg["refresh_token"])
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg["From"] = cfg.get("email", "")
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(bytes(msg)).decode("utf-8").rstrip("=")
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{API_BASE}/messages/send",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"raw": raw},
        )
        r.raise_for_status()
        data = r.json()
    return f"Sent (gmail id={data.get('id', '?')}) to {to}."
