"""Publication application service."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.creative_types import get_creative_type_registry
from app.models.creative_publication import PublicationStatus
from app.models.enums import CreativeType
from app.models.sketch_session import SketchSessionStatus
from app.models.sketch_session_event import SketchSessionEventType
from app.models.story_session import StorySessionStatus
from app.models.story_session_event import StorySessionEventType
from app.models.upload import UploadStatus
from app.models.user import User, UserStatus
from app.repositories.blocks import BlockRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.likes import LikeRepository
from app.repositories.prompts import PromptRepository
from app.repositories.publications import PublicationRepository
from app.repositories.sketch_sessions import SketchSessionRepository
from app.repositories.story_sessions import StorySessionRepository
from app.repositories.uploads import UploadRepository
from app.repositories.users import UserRepository
from app.schemas.submissions import (
    CreateSubmissionRequest,
    SketchSubmissionContent,
    StorySubmissionContent,
    SubmissionResponse,
)
from app.services.profile import ProfileService
from app.storage.base import StorageAdapter

CREATE_ENDPOINT = "POST /api/v1/submissions"


class PublicationService:
    def __init__(
        self,
        session: AsyncSession,
        clock: Clock,
        storage: StorageAdapter,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._publications = PublicationRepository(session)
        self._uploads = UploadRepository(session)
        self._sketch_sessions = SketchSessionRepository(session)
        self._story_sessions = StorySessionRepository(session)
        self._prompts = PromptRepository(session)
        self._users = UserRepository(session)
        self._likes = LikeRepository(session)
        self._blocks = BlockRepository(session)
        self._idempotency = IdempotencyRepository(session)
        self._clock = clock
        self._storage = storage
        self._settings = settings or get_settings()
        self._registry = get_creative_type_registry()

    async def create(
        self,
        *,
        user: User,
        payload: CreateSubmissionRequest,
        idempotency_key: str | None,
    ) -> tuple[SubmissionResponse, int]:
        ProfileService.require_complete_profile(user)

        request_hash = _hash_create_request(payload)
        if idempotency_key:
            existing = await self._idempotency.get(
                user_id=user.id,
                endpoint=CREATE_ENDPOINT,
                key=idempotency_key,
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise AppError(
                        code="idempotency_key_conflict",
                        message="This idempotency key was already used with a different request.",
                        status_code=409,
                    )
                return (
                    SubmissionResponse.model_validate(existing.response_body),
                    existing.response_status,
                )

        creative_type = CreativeType(payload.creative_type.value)
        self._registry.get(creative_type)

        if creative_type == CreativeType.sketch:
            response = await self._create_sketch(user, payload)
        else:
            response = await self._create_story(user, payload)

        now = self._clock.now()
        if idempotency_key:
            await self._idempotency.put(
                user_id=user.id,
                endpoint=CREATE_ENDPOINT,
                key=idempotency_key,
                request_hash=request_hash,
                response_status=201,
                response_body=response.model_dump(mode="json"),
                expires_at=now + timedelta(days=7),
            )

        return response, 201

    async def _create_sketch(
        self,
        user: User,
        payload: CreateSubmissionRequest,
    ) -> SubmissionResponse:
        if not isinstance(payload.content, SketchSubmissionContent):
            raise AppError(
                code="validation_error",
                message="Sketch submissions require sketch content.",
                status_code=422,
            )

        caption = _normalise_caption(payload.content.caption, self._settings.caption_max_length)
        sketch_session = await self._sketch_sessions.get_by_id(payload.session_id)
        if sketch_session is None or sketch_session.user_id != user.id:
            raise AppError(
                code="session_not_found",
                message="The requested sketch session could not be found.",
                status_code=404,
            )

        existing = await self._publications.get_sketch_submission_by_session_id(sketch_session.id)
        if existing is not None:
            raise AppError(
                code="session_already_submitted",
                message="This sketch session already has a published submission.",
                status_code=409,
            )

        if sketch_session.status in {
            SketchSessionStatus.abandoned,
            SketchSessionStatus.expired,
            SketchSessionStatus.completed,
        }:
            raise AppError(
                code="invalid_session_transition",
                message="That lifecycle event is not valid for the current session state.",
                status_code=422,
                details={"status": sketch_session.status.value},
            )

        upload = await self._uploads.get_by_id(payload.content.upload_id)
        if upload is None or upload.user_id != user.id:
            raise AppError(
                code="upload_not_found",
                message="The requested upload could not be found.",
                status_code=404,
            )
        if upload.status == UploadStatus.consumed:
            raise AppError(
                code="upload_already_consumed",
                message="This upload has already been used.",
                status_code=409,
            )
        if upload.status != UploadStatus.ready:
            raise AppError(
                code="upload_not_ready",
                message="This upload is not ready to publish yet.",
                status_code=422,
                details={"status": upload.status.value},
            )

        prompt = await self._prompts.get_published_by_id(sketch_session.prompt_id)
        if prompt is None:
            raise AppError(
                code="prompt_not_found",
                message="The requested prompt could not be found.",
                status_code=404,
            )

        now = self._clock.now()
        publication, _detail = await self._publications.create_sketch(
            user_id=user.id,
            prompt_id=prompt.id,
            session_id=sketch_session.id,
            sketch_session_id=sketch_session.id,
            upload_id=upload.id,
            caption=caption,
            published_at=now,
            commit=False,
        )
        await self._uploads.mark_consumed(upload, consumed_at=now, commit=False)

        await self._sketch_sessions.add_event(
            sketch_session=sketch_session,
            event_type=SketchSessionEventType.submission_created,
            occurred_at=now,
        )
        sketch_session.status = SketchSessionStatus.completed
        sketch_session.completed_at = now
        if sketch_session.upload_completed_at is None:
            sketch_session.upload_completed_at = now
        await self._sketch_sessions.save(sketch_session, commit=False)
        await self._session.commit()

        return await self._to_response(publication_id=publication.id, viewer=user)

    async def _create_story(
        self,
        user: User,
        payload: CreateSubmissionRequest,
    ) -> SubmissionResponse:
        if not isinstance(payload.content, StorySubmissionContent):
            raise AppError(
                code="validation_error",
                message="Story submissions require story content.",
                status_code=422,
            )

        if not payload.content.body or not payload.content.body.strip():
            raise AppError(
                code="validation_error",
                message="body is required for story submissions.",
                status_code=422,
            )

        caption = _normalise_caption(payload.content.caption, self._settings.caption_max_length)
        body = payload.content.body.strip()

        story_session = await self._story_sessions.get_by_id(payload.session_id)
        if story_session is None or story_session.user_id != user.id:
            raise AppError(
                code="session_not_found",
                message="The requested story session could not be found.",
                status_code=404,
            )

        existing = await self._publications.get_story_submission_by_session_id(story_session.id)
        if existing is not None:
            raise AppError(
                code="session_already_submitted",
                message="This story session already has a published submission.",
                status_code=409,
            )

        if story_session.status in {
            StorySessionStatus.completed,
            StorySessionStatus.abandoned,
            StorySessionStatus.expired,
        }:
            raise AppError(
                code="invalid_session_transition",
                message="That lifecycle event is not valid for the current session state.",
                status_code=422,
                details={"status": story_session.status.value},
            )

        prompt = await self._prompts.get_published_by_id(story_session.prompt_id)
        if prompt is None:
            raise AppError(
                code="prompt_not_found",
                message="The requested prompt could not be found.",
                status_code=404,
            )

        now = self._clock.now()
        publication, _detail = await self._publications.create_story(
            user_id=user.id,
            prompt_id=prompt.id,
            session_id=story_session.id,
            story_session_id=story_session.id,
            body=body,
            caption=caption,
            published_at=now,
            commit=False,
        )

        await self._story_sessions.add_event(
            story_session=story_session,
            event_type=StorySessionEventType.submission_created,
            occurred_at=now,
        )
        story_session.status = StorySessionStatus.completed
        story_session.completed_at = now
        await self._story_sessions.save(story_session, commit=False)
        await self._session.commit()

        return await self._to_response(publication_id=publication.id, viewer=user)

    async def get(
        self,
        *,
        submission_id: uuid.UUID,
        viewer: User | None,
    ) -> SubmissionResponse:
        return await self._to_response(publication_id=submission_id, viewer=viewer)

    async def delete(self, *, user: User, submission_id: uuid.UUID) -> None:
        publication = await self._publications.get_by_id(submission_id)
        if publication is None or publication.status == PublicationStatus.deleted:
            raise AppError(
                code="submission_not_found",
                message="The requested submission could not be found.",
                status_code=404,
            )
        if publication.user_id != user.id:
            raise AppError(
                code="submission_not_found",
                message="The requested submission could not be found.",
                status_code=404,
            )

        now = self._clock.now()
        await self._publications.soft_delete(publication, deleted_at=now)

        definition = self._registry.get(publication.creative_type)
        if definition.cleans_up_upload_on_delete:
            sketch_detail = await self._publications.get_sketch_submission(publication.id)
            if sketch_detail is not None:
                upload = await self._uploads.get_by_id(sketch_detail.upload_id)
                if upload is not None:
                    display_key = self._storage.derivative_key(
                        original_key=upload.storage_key,
                        kind="display",
                    )
                    thumbnail_key = self._storage.derivative_key(
                        original_key=upload.storage_key,
                        kind="thumbnail",
                    )
                    for key in (upload.storage_key, display_key, thumbnail_key):
                        try:
                            await self._storage.delete_object(key=key)
                        except Exception:
                            pass

    async def _to_response(
        self,
        *,
        publication_id: uuid.UUID,
        viewer: User | None,
    ) -> SubmissionResponse:
        publication = await self._publications.get_by_id(publication_id)
        if (
            publication is None
            or publication.status != PublicationStatus.published
            or publication.deleted_at is not None
        ):
            raise AppError(
                code="submission_not_found",
                message="The requested submission could not be found.",
                status_code=404,
            )

        user = await self._users.get_by_id(publication.user_id)
        prompt = await self._prompts.get_by_id(publication.prompt_id)

        sketch_session = None
        story_session = None
        sketch_detail = None
        story_detail = None
        if publication.creative_type == CreativeType.sketch:
            sketch_session = await self._sketch_sessions.get_by_id(publication.session_id)
            sketch_detail = await self._publications.get_sketch_submission(publication.id)
        else:
            story_session = await self._story_sessions.get_by_id(publication.session_id)
            story_detail = await self._publications.get_story_submission(publication.id)

        session = sketch_session or story_session

        upload = None
        if sketch_detail is not None:
            upload = await self._uploads.get_by_id(sketch_detail.upload_id)

        if (
            user is None
            or prompt is None
            or session is None
            or user.deleted_at is not None
            or user.status
            not in {
                UserStatus.incomplete,
                UserStatus.active,
            }
        ):
            raise AppError(
                code="submission_not_found",
                message="The requested submission could not be found.",
                status_code=404,
            )

        if viewer is not None and await self._blocks.either_direction_exists(
            user_a=viewer.id,
            user_b=publication.user_id,
        ):
            raise AppError(
                code="submission_not_found",
                message="The requested submission could not be found.",
                status_code=404,
            )

        image_url = None
        thumbnail_url = None
        if upload is not None:
            expires_at = self._clock.now() + timedelta(
                seconds=self._settings.signed_read_expiry_seconds
            )
            display_key = self._storage.derivative_key(
                original_key=upload.storage_key,
                kind="display",
            )
            thumbnail_key = self._storage.derivative_key(
                original_key=upload.storage_key,
                kind="thumbnail",
            )
            image_url = await self._storage.read_url(key=display_key, expires_at=expires_at)
            thumbnail_url = await self._storage.read_url(
                key=thumbnail_key,
                expires_at=expires_at,
            )

        avatar_url = None
        if user.avatar_upload_id is not None:
            avatar_expires = self._clock.now() + timedelta(
                seconds=self._settings.signed_read_expiry_seconds
            )
            avatar_upload = await self._uploads.get_by_id(user.avatar_upload_id)
            if avatar_upload is not None:
                avatar_display_key = self._storage.derivative_key(
                    original_key=avatar_upload.storage_key,
                    kind="display",
                )
                avatar_url = await self._storage.read_url(
                    key=avatar_display_key,
                    expires_at=avatar_expires,
                )

        is_owner = viewer is not None and viewer.id == publication.user_id
        viewer_has_liked = False
        if viewer is not None:
            viewer_has_liked = await self._likes.exists(
                submission_id=publication.id,
                user_id=viewer.id,
            )

        caption = None
        body = None
        upload_id = None
        if sketch_detail is not None:
            caption = sketch_detail.caption
            upload_id = sketch_detail.upload_id
        if story_detail is not None:
            caption = story_detail.caption
            body = story_detail.body

        return SubmissionResponse.from_parts(
            publication=publication,
            user=user,
            prompt=prompt,
            sketch_session=sketch_session,
            story_session=story_session,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            body=body,
            caption=caption,
            upload_id=upload_id,
            is_owner=is_owner,
            viewer_has_liked=viewer_has_liked,
            avatar_url=avatar_url,
        )


# Backward-compatible alias.
SubmissionService = PublicationService


def _hash_create_request(payload: CreateSubmissionRequest) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalise_caption(caption: str | None, max_length: int) -> str | None:
    if caption is None:
        return None
    stripped = caption.strip()
    if not stripped:
        return None
    if len(stripped) > max_length:
        raise AppError(
            code="validation_error",
            message="The request could not be validated.",
            status_code=422,
            details={"caption": "too_long"},
        )
    return stripped
