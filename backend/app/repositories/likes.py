"""Publication Like repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.publication_like import PublicationLike


class LikeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, *, submission_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(PublicationLike.publication_id).where(
                PublicationLike.publication_id == submission_id,
                PublicationLike.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def liked_submission_ids(
        self,
        *,
        user_id: uuid.UUID,
        submission_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        if not submission_ids:
            return set()
        result = await self._session.execute(
            select(PublicationLike.publication_id).where(
                PublicationLike.user_id == user_id,
                PublicationLike.publication_id.in_(submission_ids),
            )
        )
        return set(result.scalars().all())

    async def add(
        self,
        *,
        submission_id: uuid.UUID,
        user_id: uuid.UUID,
        created_at: datetime,
        commit: bool = True,
    ) -> bool:
        """Insert a Like. Returns True when a new row was inserted."""
        statement = (
            insert(PublicationLike)
            .values(
                publication_id=submission_id,
                user_id=user_id,
                created_at=created_at,
            )
            .on_conflict_do_nothing(
                index_elements=[PublicationLike.publication_id, PublicationLike.user_id]
            )
            .returning(PublicationLike.publication_id)
        )
        result = await self._session.execute(statement)
        inserted = result.scalar_one_or_none() is not None
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        return inserted

    async def delete(
        self,
        *,
        submission_id: uuid.UUID,
        user_id: uuid.UUID,
        commit: bool = True,
    ) -> bool:
        """Delete a Like. Returns True when a row was deleted."""
        existing = await self._session.get(
            PublicationLike,
            (submission_id, user_id),
        )
        if existing is None:
            return False
        await self._session.delete(existing)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        return True

    async def list_for_user(self, user_id: uuid.UUID) -> list[PublicationLike]:
        result = await self._session.execute(
            select(PublicationLike).where(PublicationLike.user_id == user_id)
        )
        return list(result.scalars().all())
