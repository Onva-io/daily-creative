"""Expire stale creative sessions of every type."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.core.settings import get_settings
from app.db.session import SessionLocal
from app.jobs.runner import job_main
from app.models.creative_session import (
    TERMINAL_SESSION_STATUSES,
    CreativeSession,
    CreativeSessionStatus,
)


async def run(dry_run: bool) -> int:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.creative_session_expiry_seconds)

    async with SessionLocal() as session:
        result = await session.execute(
            select(CreativeSession.id).where(
                CreativeSession.status.notin_(list(TERMINAL_SESSION_STATUSES)),
                CreativeSession.started_at < cutoff,
            )
        )
        ids = [row[0] for row in result.all()]
        if dry_run or not ids:
            return len(ids)
        await session.execute(
            update(CreativeSession)
            .where(CreativeSession.id.in_(ids))
            .values(status=CreativeSessionStatus.expired, abandoned_at=datetime.now(UTC))
        )
        await session.commit()
        return len(ids)


def main() -> None:
    job_main("session_cleanup", run)


if __name__ == "__main__":
    main()
