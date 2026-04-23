from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from vynaris.config import get_settings
from vynaris.db.bootstrap import create_all

log = logging.getLogger("vynaris")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_dirs()
    await create_all()
    from vynaris.adapters import start_all as start_adapters, stop_all as stop_adapters
    from vynaris.services.scheduler import reload_skill_jobs, start_scheduler, stop_scheduler
    start_scheduler()
    await reload_skill_jobs()
    await start_adapters()
    log.info("vynaris ready on %s:%s", settings.vynaris_host, settings.vynaris_port)
    yield
    await stop_adapters()
    stop_scheduler()
    from vynaris.agent.runtime import manager
    await manager.shutdown()
    log.info("vynaris shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Vynaris",
        description="Enterprise agentic work OS",
        version="0.2.0",
        docs_url=None, redoc_url=None, openapi_url=None,
        lifespan=lifespan,
    )

    static_dir = Path(__file__).parent / "web" / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    from vynaris.web.routes import (
        audit, auth, channels, data, datasources, goals, health, integrations,
        people, routines, setup_wizard, skills, teams, workspace,
    )
    app.include_router(health.router)
    app.include_router(setup_wizard.router)
    app.include_router(auth.router)
    app.include_router(people.router)
    app.include_router(teams.router)
    app.include_router(datasources.router)
    app.include_router(goals.router)
    app.include_router(skills.router)
    app.include_router(routines.router)
    app.include_router(data.router)
    app.include_router(workspace.router)
    app.include_router(audit.router)
    app.include_router(integrations.router)
    app.include_router(channels.router)

    return app


app = create_app()
