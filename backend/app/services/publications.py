"""Publication application service shared by every creative type."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.creative_types import MediaUrls, get_creative_type_registry
from app.models.creative_publication import PublicationStatus
from app.models.creative_session import TERMINAL_SESSION_STATUSES
from app.models.enums import CreativeType
from app.models.upload import Upload, UploadStatus
from app.models.user import User, UserStatus
from app.repositories.blocks import BlockRepository
from app.repositories.creative_sessions import CreativeSessionRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.likes import LikeRepository
from app.repositories.prompts import PromptRepository
from app.repositories.publications import PublicationRepository
from app.repositories.uploads import UploadRepository
from app.repositories.users import UserRepository
from app.schemas.submissions import CreateSubmissionRequest, SubmissionResponse
from app.services.creative_sessions import CreativeSessionService
from app.services.media_urls import signed_display_url, signed_thumbnail_url
from app.services.profile import ProfileService
from app.services.prompts import assert_prompt_within_window
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
        self._sessions = CreativeSessionRepository(session)
        self._session_service = CreativeSessionService(session, clock, settings)
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

        response = await self._create(user, payload)

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

    async def _create(self, user: User, payload: CreateSubmissionRequest) -> SubmissionResponse:
        creative_type = CreativeType(payload.creative_type.value)
        definition = self._registry.get(creative_type)
        if payload.content.creative_type != creative_type.value:
            raise AppError(
                code="validation_error",
                message=f"{creative_type.value.capitalize()} submissions require "
                f"{creative_type.value} content.",
                status_code=422,
            )

        caption = _normalise_caption(payload.content.caption, self._settings.caption_max_length)
        stored_content = definition.handler.validate(payload.content)

        creative_session = await self._sessions.get_by_id(payload.session_id)
        if (
            creative_session is None
            or creative_session.user_id != user.id
            or creative_session.creative_type != creative_type
        ):
            raise AppError(
                code="session_not_found",
                message="The requested session could not be found.",
                status_code=404,
            )
        if payload.prompt_id != creative_session.prompt_id:
            raise AppError(
                code="prompt_mismatch",
                message="This submission targets a different prompt than its session.",
                status_code=409,
                details={"session_prompt_id": str(creative_session.prompt_id)},
            )

        existing = await self._publications.get_by_session_id(creative_session.id)
        if existing is not None:
            raise AppError(
                code="session_already_submitted",
                message="This session already has a published submission.",
                status_code=409,
            )

        if creative_session.status in TERMINAL_SESSION_STATUSES:
            raise AppError(
                code="invalid_session_transition",
                message="That lifecycle event is not valid for the current session state.",
                status_code=422,
                details={"status": creative_session.status.value},
            )

        upload: Upload | None = None
        if definition.requires_upload:
            upload_id = getattr(payload.content, "upload_id", None)
            upload = await self._uploads.get_by_id(upload_id) if upload_id else None
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

        prompt = await self._prompts.get_published_by_id(creative_session.prompt_id)
        if prompt is None:
            raise AppError(
                code="prompt_not_found",
                message="The requested prompt could not be found.",
                status_code=404,
            )
        assert_prompt_within_window(
            prompt.prompt_date,
            today=self._clock.today(),
            backdate_days=self._settings.submission_backdate_days,
        )

        from app.models.report import ReportTargetType
        from app.services.content_moderation import ContentModerationService

        moderator = ContentModerationService(self._session, settings=self._settings)
        texts = list(definition.handler.moderation_texts(content=stored_content))
        if caption:
            texts.append((f"{creative_type.value}_caption", caption))
        for context, text in texts:
            if not text:
                continue
            await moderator.screen_text(
                text=text,
                context=context,
                target_type=ReportTargetType.submission,
                target_id=creative_session.id,
                user_id=user.id,
                commit=False,
            )

        now = self._clock.now()
        publication = await self._publications.create(
            user_id=user.id,
            prompt_id=prompt.id,
            creative_type=creative_type,
            session_id=creative_session.id,
            caption=caption,
            upload_id=upload.id if upload is not None else None,
            content=stored_content,
            published_at=now,
            commit=False,
        )
        if upload is not None:
            await self._uploads.mark_consumed(upload, consumed_at=now, commit=False)

        await self._session_service.complete_for_publication(creative_session, now=now)
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
        if (
            publication is None
            or publication.status == PublicationStatus.deleted
            or publication.user_id != user.id
        ):
            raise AppError(
                code="submission_not_found",
                message="The requested submission could not be found.",
                status_code=404,
            )

        now = self._clock.now()
        await self._publications.soft_delete(publication, deleted_at=now)

        if publication.upload_id is not None:
            upload = await self._uploads.get_by_id(publication.upload_id)
            if upload is not None:
                await delete_upload_media(self._storage, upload)

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
        creative_session = await self._sessions.get_by_id(publication.session_id)

        if (
            user is None
            or prompt is None
            or creative_session is None
            or user.deleted_at is not None
            or user.status not in {UserStatus.incomplete, UserStatus.active}
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

        expires_at = self._clock.now() + timedelta(
            seconds=self._settings.signed_read_expiry_seconds
        )

        media = MediaUrls()
        if publication.upload_id is not None:
            upload = await self._uploads.get_by_id(publication.upload_id)
            if upload is not None:
                media = MediaUrls(
                    image_url=await signed_display_url(
                        storage=self._storage,
                        original_key=upload.storage_key,
                        expires_at=expires_at,
                    ),
                    thumbnail_url=await signed_thumbnail_url(
                        storage=self._storage,
                        original_key=upload.storage_key,
                        expires_at=expires_at,
                    ),
                )

        avatar_url = None
        if user.avatar_upload_id is not None:
            avatar_upload = await self._uploads.get_by_id(user.avatar_upload_id)
            if avatar_upload is not None:
                avatar_url = await signed_display_url(
                    storage=self._storage,
                    original_key=avatar_upload.storage_key,
                    expires_at=expires_at,
                )

        is_owner = viewer is not None and viewer.id == publication.user_id
        viewer_has_liked = False
        if viewer is not None:
            viewer_has_liked = await self._likes.exists(
                submission_id=publication.id,
                user_id=viewer.id,
            )

        definition = self._registry.get(publication.creative_type)
        content = definition.handler.project(
            content=publication.content or {},
            media=media,
            is_owner=is_owner,
            preview=False,
        )

        return SubmissionResponse.from_parts(
            publication=publication,
            user=user,
            prompt=prompt,
            session=creative_session,
            content=content,
            is_owner=is_owner,
            viewer_has_liked=viewer_has_liked,
            avatar_url=avatar_url,
        )


async def delete_upload_media(storage: StorageAdapter, upload: Upload) -> None:
    """Best-effort removal of an upload's original and derivatives."""
    keys = (
        upload.storage_key,
        storage.derivative_key(original_key=upload.storage_key, kind="display"),
        storage.derivative_key(original_key=upload.storage_key, kind="thumbnail"),
    )
    for key in keys:
        try:
            await storage.delete_object(key=key)
        except Exception:
            pass


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
