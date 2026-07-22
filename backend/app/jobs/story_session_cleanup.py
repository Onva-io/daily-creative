"""Expire stale active story sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.core.settings import get_settings
from app.db.session import SessionLocal
from app.jobs.runner import job_main
from app.models.story_session import StorySession, StorySessionStatus


async def run(dry_run: bool) -> int:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.creative_session_expiry_seconds)

    async with SessionLocal() as session:
        result = await session.execute(
            select(StorySession.id).where(
                StorySession.status.in_(
                    [
                        StorySessionStatus.active,
                        StorySessionStatus.paused,
                        StorySessionStatus.writing,
                    ]
                ),
                StorySession.started_at < cutoff,
            )
        )
        ids = [row[0] for row in result.all()]
        if dry_run or not ids:
            return len(ids)
        await session.execute(
            update(StorySession)
            .where(StorySession.id.in_(ids))
            .values(status=StorySessionStatus.expired, abandoned_at=datetime.now(UTC))
        )
        await session.commit()
        return len(ids)


def main() -> None:
    job_main("story_session_cleanup", run)


if __name__ == "__main__":
    main()
