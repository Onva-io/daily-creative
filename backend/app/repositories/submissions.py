"""Submission repository."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_prompt import DailyPrompt
from app.models.enums import CreativeType
from app.models.sketch_session import SketchSession
from app.models.story_session import StorySession
from app.models.submission import Submission, SubmissionStatus, SubmissionVisibility
from app.models.upload import Upload
from app.models.user import User, UserStatus

# Authors whose public content remains visible in the community feed/detail.
_PUBLIC_AUTHOR_STATUSES = (UserStatus.incomplete, UserStatus.active)


@dataclass(frozen=True, slots=True)
class FeedRow:
    """One joined feed row loaded without N+1 queries."""

    submission: Submission
    user: User
    prompt: DailyPrompt
    sketch_session: SketchSession | None
    story_session: StorySession | None
    upload: Upload | None


class SubmissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        prompt_id: uuid.UUID,
        creative_type: CreativeType,
        sketch_session_id: uuid.UUID | None = None,
        story_session_id: uuid.UUID | None = None,
        upload_id: uuid.UUID | None = None,
        caption: str | None,
        body: str | None = None,
        published_at: datetime,
        commit: bool = True,
    ) -> Submission:
        submission = Submission(
            id=uuid.uuid4(),
            user_id=user_id,
            prompt_id=prompt_id,
            creative_type=creative_type,
            sketch_session_id=sketch_session_id,
            story_session_id=story_session_id,
            upload_id=upload_id,
            caption=caption,
            body=body,
            visibility=SubmissionVisibility.public,
            status=SubmissionStatus.published,
            like_count=0,
            reflection_count=0,
            published_at=published_at,
        )
        self._session.add(submission)
        if commit:
            await self._session.commit()
            await self._session.refresh(submission)
        else:
            await self._session.flush()
        return submission

    async def get_by_id(self, submission_id: uuid.UUID) -> Submission | None:
        result = await self._session.execute(
            select(Submission).where(Submission.id == submission_id)
        )
        return result.scalar_one_or_none()

    async def get_by_sketch_session_id(
        self,
        sketch_session_id: uuid.UUID,
    ) -> Submission | None:
        result = await self._session.execute(
            select(Submission).where(Submission.sketch_session_id == sketch_session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_story_session_id(
        self,
        story_session_id: uuid.UUID,
    ) -> Submission | None:
        result = await self._session.execute(
            select(Submission).where(Submission.story_session_id == story_session_id)
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
        creative_type: CreativeType | None = None,
    ) -> list[FeedRow]:
        """Return up to ``limit`` published feed rows in reverse-chronological order.

        Caller should request ``limit + 1`` to detect a next page.
        ``excluded_author_ids`` filters authors blocked by or blocking the viewer.
        """
        statement = self._base_feed_select()

        if creative_type is not None:
            statement = statement.where(Submission.creative_type == creative_type)

        if excluded_author_ids:
            statement = statement.where(Submission.user_id.notin_(excluded_author_ids))
        else:
            _ = viewer_id

        if cursor_published_at is not None and cursor_id is not None:
            statement = statement.where(
                or_(
                    Submission.published_at < cursor_published_at,
                    and_(
                        Submission.published_at == cursor_published_at,
                        Submission.id < cursor_id,
                    ),
                )
            )

        statement = statement.order_by(
            Submission.published_at.desc(),
            Submission.id.desc(),
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
        creative_type: CreativeType | None = None,
    ) -> list[FeedRow]:
        """Return published Submissions for one user in reverse-chronological order."""
        statement = self._base_feed_select().where(Submission.user_id == user_id)

        if creative_type is not None:
            statement = statement.where(Submission.creative_type == creative_type)

        if excluded_author_ids and user_id in excluded_author_ids:
            return []
        _ = viewer_id

        if cursor_published_at is not None and cursor_id is not None:
            statement = statement.where(
                or_(
                    Submission.published_at < cursor_published_at,
                    and_(
                        Submission.published_at == cursor_published_at,
                        Submission.id < cursor_id,
                    ),
                )
            )

        statement = statement.order_by(
            Submission.published_at.desc(),
            Submission.id.desc(),
        ).limit(limit)

        return await self._map_feed_rows(statement)

    async def count_user_published(
        self,
        user_id: uuid.UUID,
        *,
        creative_type: CreativeType | None = None,
    ) -> int:
        """Return the count of published, non-deleted public Submissions for a user."""
        stmt = (
            select(func.count())
            .select_from(Submission)
            .where(
                Submission.user_id == user_id,
                Submission.status == SubmissionStatus.published,
                Submission.deleted_at.is_(None),
                Submission.visibility == SubmissionVisibility.public,
            )
        )
        if creative_type is not None:
            stmt = stmt.where(Submission.creative_type == creative_type)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def published_prompt_dates(
        self,
        user_id: uuid.UUID,
        *,
        creative_type: CreativeType | None = None,
    ) -> list[date]:
        """Return distinct Prompt Dates with at least one published Submission."""
        stmt = (
            select(DailyPrompt.prompt_date)
            .join(Submission, Submission.prompt_id == DailyPrompt.id)
            .where(
                Submission.user_id == user_id,
                Submission.status == SubmissionStatus.published,
                Submission.deleted_at.is_(None),
                Submission.visibility == SubmissionVisibility.public,
            )
            .distinct()
            .order_by(DailyPrompt.prompt_date.desc())
        )
        if creative_type is not None:
            stmt = stmt.where(Submission.creative_type == creative_type)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _map_feed_rows(
        self,
        statement: Select[
            tuple[
                Submission,
                User,
                DailyPrompt,
                SketchSession | None,
                StorySession | None,
                Upload | None,
            ]
        ],
    ) -> list[FeedRow]:
        result = await self._session.execute(statement)
        rows: list[FeedRow] = []
        for submission, user, prompt, sketch_session, story_session, upload in result.all():
            rows.append(
                FeedRow(
                    submission=submission,
                    user=user,
                    prompt=prompt,
                    sketch_session=sketch_session,
                    story_session=story_session,
                    upload=upload,
                )
            )
        return rows

    def _base_feed_select(
        self,
    ) -> Select[
        tuple[
            Submission, User, DailyPrompt, SketchSession | None, StorySession | None, Upload | None
        ]
    ]:
        return (
            select(Submission, User, DailyPrompt, SketchSession, StorySession, Upload)
            .join(User, User.id == Submission.user_id)
            .join(DailyPrompt, DailyPrompt.id == Submission.prompt_id)
            .outerjoin(SketchSession, SketchSession.id == Submission.sketch_session_id)
            .outerjoin(StorySession, StorySession.id == Submission.story_session_id)
            .outerjoin(Upload, Upload.id == Submission.upload_id)
            .where(
                Submission.status == SubmissionStatus.published,
                Submission.deleted_at.is_(None),
                Submission.visibility == SubmissionVisibility.public,
                User.status.in_(_PUBLIC_AUTHOR_STATUSES),
                User.deleted_at.is_(None),
            )
        )

    async def soft_delete(self, submission: Submission, *, deleted_at: datetime) -> Submission:
        submission.status = SubmissionStatus.deleted
        submission.deleted_at = deleted_at
        await self._session.commit()
        await self._session.refresh(submission)
        return submission

    async def list_published_for_user_ids(self, user_id: uuid.UUID) -> list[Submission]:
        result = await self._session.execute(
            select(Submission).where(
                Submission.user_id == user_id,
                Submission.status == SubmissionStatus.published,
                Submission.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def set_status(
        self,
        submission: Submission,
        *,
        status: SubmissionStatus,
        deleted_at: datetime | None = None,
        commit: bool = True,
    ) -> Submission:
        submission.status = status
        if deleted_at is not None:
            submission.deleted_at = deleted_at
        elif status == SubmissionStatus.published:
            submission.deleted_at = None
        if commit:
            await self._session.commit()
            await self._session.refresh(submission)
        else:
            await self._session.flush()
        return submission

    async def save(self, submission: Submission) -> Submission:
        await self._session.commit()
        await self._session.refresh(submission)
        return submission
