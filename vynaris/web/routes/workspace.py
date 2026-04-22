from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.config import get_settings
from vynaris.db import get_db
from vynaris.db.models import Person
from vynaris.services.workspace import ensure_workspace, safe_relative
from vynaris.web.deps import current_person
from vynaris.web.routes.channels import _build_sidebar
from vynaris.web.templating import render

router = APIRouter()
settings = get_settings()


def _list_tree(root: Path, limit: int = 200) -> list[dict]:
    items: list[dict] = []
    if not root.exists():
        return items
    for p in sorted(root.rglob("*")):
        if len(items) >= limit:
            break
        if p.is_dir():
            continue
        rel = p.relative_to(root).as_posix()
        parts = rel.split("/")
        scope = "private" if parts[0] == "private" else ("public" if parts[0] == "public" else "root")
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        items.append({"rel": rel, "scope": scope, "size": size})
    return items


@router.get("/workspace/{person_id}", response_class=HTMLResponse)
async def workspace_view(
    person_id: uuid.UUID,
    request: Request,
    path: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    viewer = await current_person(request, db)
    if viewer is None:
        return RedirectResponse("/login", status_code=303)
    target = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
    if target is None or target.org_id != viewer.org_id:
        return RedirectResponse("/people", status_code=303)

    can_see_private = viewer.is_admin or viewer.id == target.id
    root = ensure_workspace(target.id)

    files = _list_tree(root)
    if not can_see_private:
        files = [f for f in files if f["scope"] != "private"]

    selected_content: str | None = None
    selected_path: str | None = None
    if path:
        try:
            target_path = safe_relative(root, path)
            if target_path.exists() and target_path.is_file():
                if not can_see_private and target_path.is_relative_to(root / "private"):
                    selected_content = "(private — only owner + admin can view)"
                else:
                    try:
                        raw = target_path.read_text(encoding="utf-8", errors="replace")
                        selected_content = raw[:200000]
                        selected_path = path
                    except Exception as e:
                        selected_content = f"(unreadable: {e})"
        except Exception as e:
            selected_content = f"(invalid path: {e})"

    sidebar = await _build_sidebar(db, viewer)
    return render(
        request, "workspace.html",
        viewer=viewer, target=target,
        files=files, selected_content=selected_content, selected_path=selected_path,
        can_see_private=can_see_private, sidebar=sidebar,
    )
