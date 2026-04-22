"""No seed. Vynaris starts empty; first user creates their org via /setup."""

AVATAR_COLORS = [
    "#6366f1", "#ec4899", "#14b8a6", "#f59e0b", "#8b5cf6",
    "#22c55e", "#ef4444", "#06b6d4", "#eab308", "#f97316",
    "#a855f7", "#10b981",
]


async def maybe_seed_demo() -> None:
    """Intentionally a no-op. Retained for compatibility with app.lifespan."""
    return
