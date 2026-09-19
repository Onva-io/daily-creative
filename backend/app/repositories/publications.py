"""Creative publication repository."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creative_publication import (
    CreativePublication,
    PublicationStatus,
    PublicationVisibility,
)
from app.models.creative_session import CreativeSession
from app.models.daily_prompt import DailyPrompt
from app.models.enums import CreativeType
from app.models.upload import Upload
from app.models.user import User, UserStatus

_PUBLIC_AUTHOR_STATUSES = (UserStatus.incomplete, UserStatus.active)


@dataclass(frozen=True, slots=True)
class FeedRow:
    """One joined feed row loaded without N+1 queries."""

    publication: CreativePublication
    user: User
    prompt: DailyPrompt
    session: CreativeSession | None
    upload: Upload | None


class PublicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        prompt_id: uuid.UUID,
        creative_type: CreativeType,
        session_id: uuid.UUID,
        caption: str | None,
        upload_id: uuid.UUID | None,
        content: dict[str, Any],
        published_at: datetime,
        commit: bool = True,
    ) -> CreativePublication:
        publication = CreativePublication(
            id=uuid.uuid4(),
            user_id=user_id,
            prompt_id=prompt_id,
            creative_type=creative_type,
            session_id=session_id,
            caption=caption,
            upload_id=upload_id,
            content=content,
            visibility=PublicationVisibility.public,
            status=PublicationStatus.published,
            like_count=0,
            reflection_count=0,
            published_at=published_at,
        )
        self._session.add(publication)
        if commit:
            await self._session.commit()
            await self._session.refresh(publication)
        else:
            await self._session.flush()
        return publication

    async def get_by_id(self, publication_id: uuid.UUID) -> CreativePublication | None:
        result = await self._session.execute(
            select(CreativePublication).where(CreativePublication.id == publication_id)
        )
        return result.scalar_one_or_none()

    async def get_by_session_id(self, session_id: uuid.UUID) -> CreativePublication | None:
        result = await self._session.execute(
            select(CreativePublication).where(CreativePublication.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_recent_published(
        self,
        *,
        limit: int,
        cursor_published_at: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
        viewer_id: uuid.UUID | None = None,
        excluded_author_ids: set[uuid.UUID] | None = None,
        creative_type: CreativeType,
    ) -> list[FeedRow]:
        statement = self._base_feed_select().where(
            CreativePublication.creative_type == creative_type
        )

        if excluded_author_ids:
            statement = statement.where(CreativePublication.user_id.notin_(excluded_author_ids))
        else:
            _ = viewer_id

        if cursor_published_at is not None and cursor_id is not None:
            statement = statement.where(
                or_(
                    CreativePublication.published_at < cursor_published_at,
                    and_(
                        CreativePublication.published_at == cursor_published_at,
                        CreativePublication.id < cursor_id,
                    ),
                )
            )

        statement = statement.order_by(
            CreativePublication.published_at.desc(),
            CreativePublication.id.desc(),
        ).limit(limit)

        return await self._map_feed_rows(statement)

    async def list_user_published(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        cursor_published_at: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
        viewer_id: uuid.UUID | None = None,
        excluded_author_ids: set[uuid.UUID] | None = None,
        creative_type: CreativeType,
    ) -> list[FeedRow]:
        statement = self._base_feed_select().where(
            CreativePublication.user_id == user_id,
            CreativePublication.creative_type == creative_type,
        )

        if excluded_author_ids and user_id in excluded_author_ids:
            return []
        _ = viewer_id

        if cursor_published_at is not None and cursor_id is not None:
            statement = statement.where(
                or_(
                    CreativePublication.published_at < cursor_published_at,
                    and_(
                        CreativePublication.published_at == cursor_published_at,
                        CreativePublication.id < cursor_id,
                    ),
                )
            )

        statement = statement.order_by(
            CreativePublication.published_at.desc(),
            CreativePublication.id.desc(),
        ).limit(limit)

        return await self._map_feed_rows(statement)

    async def count_user_published(
        self,
        user_id: uuid.UUID,
        *,
        creative_type: CreativeType,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(CreativePublication)
            .where(
                CreativePublication.user_id == user_id,
                CreativePublication.status == PublicationStatus.published,
                CreativePublication.deleted_at.is_(None),
                CreativePublication.visibility == PublicationVisibility.public,
                CreativePublication.creative_type == creative_type,
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def published_prompt_dates(
        self,
        user_id: uuid.UUID,
        *,
        creative_type: CreativeType,
    ) -> list[date]:
        stmt = (
            select(DailyPrompt.prompt_date)
            .join(CreativePublication, CreativePublication.prompt_id == DailyPrompt.id)
            .where(
                CreativePublication.user_id == user_id,
                CreativePublication.status == PublicationStatus.published,
                CreativePublication.deleted_at.is_(None),
                CreativePublication.visibility == PublicationVisibility.public,
                CreativePublication.creative_type == creative_type,
            )
            .distinct()
            .order_by(DailyPrompt.prompt_date.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _map_feed_rows(self, statement: Select[Any]) -> list[FeedRow]:
        result = await self._session.execute(statement)
        return [
            FeedRow(
                publication=publication,
                user=user,
                prompt=prompt,
                session=session,
                upload=upload,
            )
            for publication, user, prompt, session, upload in result.all()
        ]

    def _base_feed_select(self) -> Select[Any]:
        return (
            select(CreativePublication, User, DailyPrompt, CreativeSession, Upload)
            .join(User, User.id == CreativePublication.user_id)
            .join(DailyPrompt, DailyPrompt.id == CreativePublication.prompt_id)
            .outerjoin(CreativeSession, CreativeSession.id == CreativePublication.session_id)
            .outerjoin(Upload, Upload.id == CreativePublication.upload_id)
            .where(
                CreativePublication.status == PublicationStatus.published,
                CreativePublication.deleted_at.is_(None),
                CreativePublication.visibility == PublicationVisibility.public,
                User.status.in_(_PUBLIC_AUTHOR_STATUSES),
                User.deleted_at.is_(None),
            )
        )

    async def soft_delete(
        self,
        publication: CreativePublication,
        *,
        deleted_at: datetime,
    ) -> CreativePublication:
        publication.status = PublicationStatus.deleted
        publication.deleted_at = deleted_at
        await self._session.commit()
        await self._session.refresh(publication)
        return publication

    async def list_all_for_user(self, user_id: uuid.UUID) -> list[CreativePublication]:
        result = await self._session.execute(
            select(CreativePublication).where(CreativePublication.user_id == user_id)
        )
        return list(result.scalars().all())

    async def list_published_for_user_ids(
        self,
        user_id: uuid.UUID,
    ) -> list[CreativePublication]:
        result = await self._session.execute(
            select(CreativePublication).where(
                CreativePublication.user_id == user_id,
                CreativePublication.status == PublicationStatus.published,
                CreativePublication.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def set_status(
        self,
        publication: CreativePublication,
        *,
        status: PublicationStatus,
        deleted_at: datetime | None = None,
        commit: bool = True,
    ) -> CreativePublication:
        publication.status = status
        if deleted_at is not None:
            publication.deleted_at = deleted_at
        elif status == PublicationStatus.published:
            publication.deleted_at = None
        if commit:
            await self._session.commit()
            await self._session.refresh(publication)
        else:
            await self._session.flush()
        return publication

    async def save(self, publication: CreativePublication) -> CreativePublication:
        await self._session.commit()
        await self._session.refresh(publication)
        return publication


# Backward-compatible alias.
SubmissionRepository = PublicationRepository
