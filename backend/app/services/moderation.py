"""Operator moderation service (internal only)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import AppError
from app.models.creative_publication import PublicationStatus
from app.models.enums import CreativeType
from app.models.moderation_action import ModerationActionType
from app.models.moderation_review import ModerationReviewStatus
from app.models.reflection import ReflectionStatus
from app.models.report import ReportStatus, ReportTargetType
from app.models.user import UserStatus
from app.repositories.moderation_actions import ModerationActionRepository
from app.repositories.moderation_reviews import ModerationReviewRepository
from app.repositories.publications import PublicationRepository
from app.repositories.reflections import ReflectionRepository
from app.repositories.reports import ReportRepository
from app.repositories.users import UserRepository


class ModerationService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock
        self._reports = ReportRepository(session)
        self._actions = ModerationActionRepository(session)
        self._reviews = ModerationReviewRepository(session)
        self._publications = PublicationRepository(session)
        self._reflections = ReflectionRepository(session)
        self._users = UserRepository(session)

    async def list_open_reports(self, *, limit: int = 50) -> list[dict[str, Any]]:
        reports = await self._reports.list_open(limit=limit)
        return [
            {
                "id": str(report.id),
                "reporter_user_id": str(report.reporter_user_id),
                "target_type": report.target_type.value,
                "target_id": str(report.target_id),
                "reason": report.reason.value,
                "notes": report.notes,
                "status": report.status.value,
                "created_at": report.created_at.isoformat(),
            }
            for report in reports
        ]

    async def list_review_queue(self, *, limit: int = 50) -> list[dict[str, Any]]:
        items = await self._reviews.list_open(limit=limit)
        enriched: list[dict[str, Any]] = []
        for item in items:
            preview: dict[str, Any] = {}
            try:
                target = await self.inspect_target(
                    target_type=item.target_type,
                    target_id=item.target_id,
                )
                for key in (
                    "caption",
                    "body",
                    "status",
                    "username",
                    "display_name",
                    "creative_type",
                ):
                    if key in target and target[key] is not None:
                        preview[key] = target[key]
            except AppError:
                preview = {"missing": True}
            enriched.append(
                {
                    "id": str(item.id),
                    "target_type": item.target_type.value,
                    "target_id": str(item.target_id),
                    "user_id": str(item.user_id) if item.user_id else None,
                    "confidence": item.confidence,
                    "categories": item.categories,
                    "provider": item.provider,
                    "created_at": item.created_at.isoformat(),
                    "preview": preview,
                }
            )
        return enriched

    async def inspect_target(
        self,
        *,
        target_type: ReportTargetType,
        target_id: uuid.UUID,
    ) -> dict[str, Any]:
        if target_type == ReportTargetType.submission:
            submission = await self._publications.get_by_id(target_id)
            if submission is None:
                raise AppError(
                    code="report_target_not_found",
                    message="The requested target could not be found.",
                    status_code=404,
                )
            caption: str | None = None
            body: str | None = None
            if submission.creative_type == CreativeType.sketch:
                sketch = await self._publications.get_sketch_submission(submission.id)
                caption = sketch.caption if sketch is not None else None
            elif submission.creative_type == CreativeType.story:
                story = await self._publications.get_story_submission(submission.id)
                if story is not None:
                    caption = story.caption
                    body = story.body
            return {
                "target_type": "submission",
                "id": str(submission.id),
                "user_id": str(submission.user_id),
                "status": submission.status.value,
                "creative_type": submission.creative_type.value,
                "caption": caption,
                "body": body,
                "published_at": submission.published_at.isoformat(),
                "deleted_at": (
                    submission.deleted_at.isoformat() if submission.deleted_at else None
                ),
            }
        if target_type == ReportTargetType.reflection:
            reflection = await self._reflections.get_by_id(target_id)
            if reflection is None:
                raise AppError(
                    code="report_target_not_found",
                    message="The requested target could not be found.",
                    status_code=404,
                )
            return {
                "target_type": "reflection",
                "id": str(reflection.id),
                "submission_id": str(reflection.submission_id),
                "user_id": str(reflection.user_id),
                "status": reflection.status.value,
                "body": reflection.body,
                "created_at": reflection.created_at.isoformat(),
            }
        user = await self._users.get_by_id(target_id)
        if user is None:
            raise AppError(
                code="report_target_not_found",
                message="The requested target could not be found.",
                status_code=404,
            )
        return {
            "target_type": "profile",
            "id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
            "status": user.status.value,
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
        }

    async def hide_submission(
        self,
        *,
        operator_identity: str,
        submission_id: uuid.UUID,
        reason: str,
        report_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        return await self._set_submission_status(
            operator_identity=operator_identity,
            submission_id=submission_id,
            status=PublicationStatus.hidden,
            action=ModerationActionType.hide_submission,
            reason=reason,
            report_id=report_id,
            commit=commit,
        )

    async def remove_submission(
        self,
        *,
        operator_identity: str,
        submission_id: uuid.UUID,
        reason: str,
        report_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        return await self._set_submission_status(
            operator_identity=operator_identity,
            submission_id=submission_id,
            status=PublicationStatus.removed,
            action=ModerationActionType.remove_submission,
            reason=reason,
            report_id=report_id,
            commit=commit,
        )

    async def restore_submission(
        self,
        *,
        operator_identity: str,
        submission_id: uuid.UUID,
        reason: str,
        report_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        return await self._set_submission_status(
            operator_identity=operator_identity,
            submission_id=submission_id,
            status=PublicationStatus.published,
            action=ModerationActionType.restore_submission,
            reason=reason,
            report_id=report_id,
            clear_deleted_at=True,
            commit=commit,
        )

    async def hide_reflection(
        self,
        *,
        operator_identity: str,
        reflection_id: uuid.UUID,
        reason: str,
        report_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        return await self._set_reflection_status(
            operator_identity=operator_identity,
            reflection_id=reflection_id,
            status=ReflectionStatus.hidden,
            action=ModerationActionType.hide_reflection,
            reason=reason,
            report_id=report_id,
            adjust_counter=-1,
            commit=commit,
        )

    async def remove_reflection(
        self,
        *,
        operator_identity: str,
        reflection_id: uuid.UUID,
        reason: str,
        report_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        return await self._set_reflection_status(
            operator_identity=operator_identity,
            reflection_id=reflection_id,
            status=ReflectionStatus.removed,
            action=ModerationActionType.remove_reflection,
            reason=reason,
            report_id=report_id,
            adjust_counter=-1,
            commit=commit,
        )

    async def restore_reflection(
        self,
        *,
        operator_identity: str,
        reflection_id: uuid.UUID,
        reason: str,
        report_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        return await self._set_reflection_status(
            operator_identity=operator_identity,
            reflection_id=reflection_id,
            status=ReflectionStatus.published,
            action=ModerationActionType.restore_reflection,
            reason=reason,
            report_id=report_id,
            adjust_counter=1,
            clear_deleted_at=True,
            commit=commit,
        )

    async def suspend_user(
        self,
        *,
        operator_identity: str,
        user_id: uuid.UUID,
        reason: str,
        report_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise AppError(
                code="user_not_found",
                message="The requested user could not be found.",
                status_code=404,
            )
        await self._users.set_status(user, status=UserStatus.suspended, commit=False)
        await self._actions.record(
            operator_identity=operator_identity,
            action=ModerationActionType.suspend_user,
            target_type=ReportTargetType.profile,
            target_id=user_id,
            reason=reason,
            report_id=report_id,
            commit=False,
        )
        await self._session.commit()
        return {"user_id": str(user_id), "status": UserStatus.suspended.value}

    async def restore_user(
        self,
        *,
        operator_identity: str,
        user_id: uuid.UUID,
        reason: str,
        report_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise AppError(
                code="user_not_found",
                message="The requested user could not be found.",
                status_code=404,
            )
        new_status = (
            UserStatus.active if user.profile_completed_at is not None else UserStatus.incomplete
        )
        await self._users.set_status(user, status=new_status, commit=False)
        await self._actions.record(
            operator_identity=operator_identity,
            action=ModerationActionType.restore_user,
            target_type=ReportTargetType.profile,
            target_id=user_id,
            reason=reason,
            report_id=report_id,
            commit=False,
        )
        await self._session.commit()
        return {"user_id": str(user_id), "status": new_status.value}

    async def resolve_report(
        self,
        *,
        operator_identity: str,
        report_id: uuid.UUID,
        resolution_notes: str,
        dismiss: bool = False,
        reviewer_user_id: uuid.UUID | None = None,
        commit: bool = True,
        action: ModerationActionType | None = None,
    ) -> dict[str, Any]:
        report = await self._reports.get_by_id(report_id)
        if report is None:
            raise AppError(
                code="report_target_not_found",
                message="The requested report could not be found.",
                status_code=404,
            )
        status = ReportStatus.dismissed if dismiss else ReportStatus.resolved
        recorded_action = action or (
            ModerationActionType.dismiss_report if dismiss else ModerationActionType.resolve_report
        )
        await self._reports.mark_reviewed(
            report,
            status=status,
            reviewed_at=self._clock.now(),
            reviewed_by_user_id=reviewer_user_id,
            resolution_notes=resolution_notes,
            commit=False,
        )
        await self._actions.record(
            operator_identity=operator_identity,
            action=recorded_action,
            target_type=report.target_type,
            target_id=report.target_id,
            reason=resolution_notes,
            report_id=report.id,
            commit=False,
        )
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        return {"report_id": str(report.id), "status": status.value}

    async def approve_reported_content(
        self,
        *,
        operator_identity: str,
        report_id: uuid.UUID,
        reason: str,
        reviewer_user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        report = await self._reports.get_by_id(report_id)
        if report is None:
            raise AppError(
                code="report_target_not_found",
                message="The requested report could not be found.",
                status_code=404,
            )
        if report.target_type == ReportTargetType.submission:
            submission = await self._publications.get_by_id(report.target_id)
            if submission is not None and submission.status in (
                PublicationStatus.hidden,
                PublicationStatus.removed,
            ):
                await self._publications.set_status(
                    submission,
                    status=PublicationStatus.published,
                    deleted_at=None,
                    commit=False,
                )
        elif report.target_type == ReportTargetType.reflection:
            reflection = await self._reflections.get_by_id(report.target_id)
            if reflection is not None and reflection.status in (
                ReflectionStatus.hidden,
                ReflectionStatus.removed,
            ):
                await self._reflections.set_moderation_status(
                    reflection,
                    status=ReflectionStatus.published,
                    deleted_at=None,
                    commit=False,
                )
                submission = await self._publications.get_by_id(reflection.submission_id)
                if submission is not None:
                    submission.reflection_count = submission.reflection_count + 1
        result = await self.resolve_report(
            operator_identity=operator_identity,
            report_id=report_id,
            resolution_notes=reason,
            dismiss=True,
            reviewer_user_id=reviewer_user_id,
            commit=False,
            action=ModerationActionType.approve_reported_content,
        )
        await self._session.commit()
        return result

    async def approve_review_item(
        self,
        *,
        operator_identity: str,
        item_id: uuid.UUID,
        reason: str,
    ) -> dict[str, Any]:
        item = await self._reviews.get_by_id(item_id)
        if item is None or item.status != ModerationReviewStatus.open:
            raise AppError(
                code="review_item_not_found",
                message="The requested review queue item could not be found.",
                status_code=404,
            )
        await self._reviews.resolve(
            item,
            status=ModerationReviewStatus.resolved,
            resolved_at=self._clock.now(),
            commit=False,
        )
        await self._actions.record(
            operator_identity=operator_identity,
            action=ModerationActionType.approve_review_item,
            target_type=item.target_type,
            target_id=item.target_id,
            reason=reason,
            commit=False,
        )
        await self._session.commit()
        return {
            "id": str(item.id),
            "status": ModerationReviewStatus.resolved.value,
            "target_type": item.target_type.value,
            "target_id": str(item.target_id),
        }

    async def reject_review_item(
        self,
        *,
        operator_identity: str,
        item_id: uuid.UUID,
        reason: str,
        remove: bool = False,
    ) -> dict[str, Any]:
        item = await self._reviews.get_by_id(item_id)
        if item is None or item.status != ModerationReviewStatus.open:
            raise AppError(
                code="review_item_not_found",
                message="The requested review queue item could not be found.",
                status_code=404,
            )
        if item.target_type == ReportTargetType.submission:
            if remove:
                await self.remove_submission(
                    operator_identity=operator_identity,
                    submission_id=item.target_id,
                    reason=reason,
                    commit=False,
                )
            else:
                await self.hide_submission(
                    operator_identity=operator_identity,
                    submission_id=item.target_id,
                    reason=reason,
                    commit=False,
                )
        elif item.target_type == ReportTargetType.reflection:
            if remove:
                await self.remove_reflection(
                    operator_identity=operator_identity,
                    reflection_id=item.target_id,
                    reason=reason,
                    commit=False,
                )
            else:
                await self.hide_reflection(
                    operator_identity=operator_identity,
                    reflection_id=item.target_id,
                    reason=reason,
                    commit=False,
                )

        await self._reviews.resolve(
            item,
            status=ModerationReviewStatus.dismissed,
            resolved_at=self._clock.now(),
            commit=False,
        )
        await self._actions.record(
            operator_identity=operator_identity,
            action=ModerationActionType.reject_review_item,
            target_type=item.target_type,
            target_id=item.target_id,
            reason=reason,
            commit=False,
        )
        await self._session.commit()
        return {
            "id": str(item.id),
            "status": ModerationReviewStatus.dismissed.value,
            "target_type": item.target_type.value,
            "target_id": str(item.target_id),
            "removed": remove,
        }

    async def redact_caption(
        self,
        *,
        operator_identity: str,
        submission_id: uuid.UUID,
        reason: str,
        report_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        submission = await self._publications.get_by_id(submission_id)
        if submission is None:
            raise AppError(
                code="submission_not_found",
                message="The requested sketch could not be found.",
                status_code=404,
            )
        if submission.creative_type == CreativeType.sketch:
            sketch = await self._publications.get_sketch_submission(submission.id)
            if sketch is None:
                raise AppError(
                    code="submission_not_found",
                    message="The requested sketch could not be found.",
                    status_code=404,
                )
            sketch.caption = None
        elif submission.creative_type == CreativeType.story:
            story = await self._publications.get_story_submission(submission.id)
            if story is None:
                raise AppError(
                    code="submission_not_found",
                    message="The requested sketch could not be found.",
                    status_code=404,
                )
            story.caption = None
        else:
            raise AppError(
                code="validation_error",
                message="This creative type does not support captions.",
                status_code=422,
            )
        await self._actions.record(
            operator_identity=operator_identity,
            action=ModerationActionType.redact_caption,
            target_type=ReportTargetType.submission,
            target_id=submission_id,
            reason=reason,
            report_id=report_id,
            commit=False,
        )
        await self._session.commit()
        return {"submission_id": str(submission_id), "caption": None}

    async def _set_submission_status(
        self,
        *,
        operator_identity: str,
        submission_id: uuid.UUID,
        status: PublicationStatus,
        action: ModerationActionType,
        reason: str,
        report_id: uuid.UUID | None,
        clear_deleted_at: bool = False,
        commit: bool = True,
    ) -> dict[str, Any]:
        submission = await self._publications.get_by_id(submission_id)
        if submission is None:
            raise AppError(
                code="submission_not_found",
                message="The requested sketch could not be found.",
                status_code=404,
            )
        deleted_at = None if clear_deleted_at else submission.deleted_at
        await self._publications.set_status(
            submission,
            status=status,
            deleted_at=deleted_at,
            commit=False,
        )
        await self._actions.record(
            operator_identity=operator_identity,
            action=action,
            target_type=ReportTargetType.submission,
            target_id=submission_id,
            reason=reason,
            report_id=report_id,
            commit=False,
        )
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        return {"submission_id": str(submission_id), "status": status.value}

    async def _set_reflection_status(
        self,
        *,
        operator_identity: str,
        reflection_id: uuid.UUID,
        status: ReflectionStatus,
        action: ModerationActionType,
        reason: str,
        report_id: uuid.UUID | None,
        adjust_counter: int = 0,
        clear_deleted_at: bool = False,
        commit: bool = True,
    ) -> dict[str, Any]:
        reflection = await self._reflections.get_by_id(reflection_id)
        if reflection is None:
            raise AppError(
                code="reflection_not_found",
                message="The requested reflection could not be found.",
                status_code=404,
            )
        previous = reflection.status
        deleted_at = None if clear_deleted_at else reflection.deleted_at
        await self._reflections.set_moderation_status(
            reflection,
            status=status,
            deleted_at=deleted_at,
            commit=False,
        )
        if adjust_counter and previous != status:
            submission = await self._publications.get_by_id(reflection.submission_id)
            if submission is not None:
                if adjust_counter < 0 and previous == ReflectionStatus.published:
                    submission.reflection_count = max(0, submission.reflection_count - 1)
                elif adjust_counter > 0 and status == ReflectionStatus.published:
                    submission.reflection_count = submission.reflection_count + 1
        await self._actions.record(
            operator_identity=operator_identity,
            action=action,
            target_type=ReportTargetType.reflection,
            target_id=reflection_id,
            reason=reason,
            report_id=report_id,
            commit=False,
        )
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        return {"reflection_id": str(reflection_id), "status": status.value}
