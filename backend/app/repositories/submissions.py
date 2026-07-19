"""Submission repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.submission import Submission, SubmissionStatus, SubmissionVisibility


class SubmissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        prompt_id: uuid.UUID,
        sketch_session_id: uuid.UUID,
        upload_id: uuid.UUID,
        caption: str | None,
        published_at: datetime,
        commit: bool = True,
    ) -> Submission:
        submission = Submission(
            id=uuid.uuid4(),
            user_id=user_id,
            prompt_id=prompt_id,
            sketch_session_id=sketch_session_id,
            upload_id=upload_id,
            caption=caption,
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

    async def soft_delete(self, submission: Submission, *, deleted_at: datetime) -> Submission:
        submission.status = SubmissionStatus.deleted
        submission.deleted_at = deleted_at
        await self._session.commit()
        await self._session.refresh(submission)
        return submission

    async def save(self, submission: Submission) -> Submission:
        await self._session.commit()
        await self._session.refresh(submission)
        return submission
