"""Internal operator moderation endpoints (not part of the public OpenAPI contract)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.operator import OperatorPrincipal, require_moderation_operator
from app.core.clock import Clock, get_clock
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.db.session import get_db_session
from app.models.report import ReportTargetType
from app.services.moderation import ModerationService

router = APIRouter(prefix="/internal/moderation", tags=["moderation"])


class ModerationActionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    report_id: UUID | None = None


class ResolveReportRequest(BaseModel):
    resolution_notes: str = Field(min_length=1, max_length=2000)
    dismiss: bool = False


class ApproveRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class RejectReviewRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    remove: bool = False


@router.get("/reports")
async def list_reports(
    _operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    limit: int = 50,
) -> dict[str, Any]:
    items = await ModerationService(session, clock).list_open_reports(limit=limit)
    return {"items": items}


@router.get("/targets/{target_type}/{target_id}")
async def inspect_target(
    target_type: ReportTargetType,
    target_id: UUID,
    _operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).inspect_target(
        target_type=target_type,
        target_id=target_id,
    )


@router.post("/submissions/{submission_id}/hide")
async def hide_submission(
    submission_id: UUID,
    payload: ModerationActionRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).hide_submission(
        operator_identity=operator.identity,
        submission_id=submission_id,
        reason=payload.reason,
        report_id=payload.report_id,
    )


@router.post("/submissions/{submission_id}/remove")
async def remove_submission(
    submission_id: UUID,
    payload: ModerationActionRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).remove_submission(
        operator_identity=operator.identity,
        submission_id=submission_id,
        reason=payload.reason,
        report_id=payload.report_id,
    )


@router.post("/submissions/{submission_id}/restore")
async def restore_submission(
    submission_id: UUID,
    payload: ModerationActionRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).restore_submission(
        operator_identity=operator.identity,
        submission_id=submission_id,
        reason=payload.reason,
        report_id=payload.report_id,
    )


@router.post("/submissions/{submission_id}/redact-caption")
async def redact_caption(
    submission_id: UUID,
    payload: ModerationActionRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).redact_caption(
        operator_identity=operator.identity,
        submission_id=submission_id,
        reason=payload.reason,
        report_id=payload.report_id,
    )


@router.post("/reflections/{reflection_id}/hide")
async def hide_reflection(
    reflection_id: UUID,
    payload: ModerationActionRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).hide_reflection(
        operator_identity=operator.identity,
        reflection_id=reflection_id,
        reason=payload.reason,
        report_id=payload.report_id,
    )


@router.post("/reflections/{reflection_id}/remove")
async def remove_reflection(
    reflection_id: UUID,
    payload: ModerationActionRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).remove_reflection(
        operator_identity=operator.identity,
        reflection_id=reflection_id,
        reason=payload.reason,
        report_id=payload.report_id,
    )


@router.post("/reflections/{reflection_id}/restore")
async def restore_reflection(
    reflection_id: UUID,
    payload: ModerationActionRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).restore_reflection(
        operator_identity=operator.identity,
        reflection_id=reflection_id,
        reason=payload.reason,
        report_id=payload.report_id,
    )


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: UUID,
    payload: ModerationActionRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).suspend_user(
        operator_identity=operator.identity,
        user_id=user_id,
        reason=payload.reason,
        report_id=payload.report_id,
    )


@router.post("/users/{user_id}/restore")
async def restore_user(
    user_id: UUID,
    payload: ModerationActionRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).restore_user(
        operator_identity=operator.identity,
        user_id=user_id,
        reason=payload.reason,
        report_id=payload.report_id,
    )


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: UUID,
    payload: ResolveReportRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).resolve_report(
        operator_identity=operator.identity,
        report_id=report_id,
        resolution_notes=payload.resolution_notes,
        dismiss=payload.dismiss,
        reviewer_user_id=operator.user_id,
    )


@router.post("/reports/{report_id}/approve")
async def approve_reported_content(
    report_id: UUID,
    payload: ApproveRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).approve_reported_content(
        operator_identity=operator.identity,
        report_id=report_id,
        reason=payload.reason,
        reviewer_user_id=operator.user_id,
    )


class CreatePolicyDraftRequest(BaseModel):
    kind: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    body_markdown: str = Field(min_length=1)
    minimum_age: int = Field(default=13, ge=1, le=120)
    is_significant_change: bool = False
    change_summary: str | None = Field(default=None, max_length=2000)


@router.get("/policies")
async def list_policies(
    kind: str | None = None,
    _operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from app.models.policy import PolicyKind
    from app.services.policies import PolicyService

    policy_kind = PolicyKind(kind) if kind else None
    documents = await PolicyService(session, clock=clock, settings=settings).list_documents(
        kind=policy_kind
    )
    return {
        "items": [
            {
                "id": str(doc.id),
                "kind": doc.kind.value,
                "version": doc.version,
                "title": doc.title,
                "status": doc.status.value,
                "minimum_age": doc.minimum_age,
                "is_significant_change": doc.is_significant_change,
                "change_summary": doc.change_summary,
                "published_at": doc.published_at.isoformat() if doc.published_at else None,
                "content_hash": doc.content_hash,
            }
            for doc in documents
        ]
    }


@router.post("/policies")
async def create_policy_draft(
    payload: CreatePolicyDraftRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from app.models.policy import PolicyKind
    from app.services.policies import PolicyService

    try:
        kind = PolicyKind(payload.kind)
    except ValueError as exc:
        raise AppError(
            code="validation_error",
            message="Unknown policy kind.",
            status_code=422,
        ) from exc
    document = await PolicyService(session, clock=clock, settings=settings).create_draft(
        kind=kind,
        version=payload.version,
        title=payload.title,
        body_markdown=payload.body_markdown,
        minimum_age=payload.minimum_age,
        is_significant_change=payload.is_significant_change,
        change_summary=payload.change_summary,
        operator_identity=operator.identity,
    )
    return {
        "id": str(document.id),
        "kind": document.kind.value,
        "version": document.version,
        "status": document.status.value,
    }


@router.post("/policies/{document_id}/publish")
async def publish_policy(
    document_id: UUID,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    from app.services.policies import PolicyService

    document = await PolicyService(session, clock=clock, settings=settings).publish(
        document_id,
        operator_identity=operator.identity,
    )
    return {
        "id": str(document.id),
        "kind": document.kind.value,
        "version": document.version,
        "status": document.status.value,
        "is_significant_change": document.is_significant_change,
        "published_at": document.published_at.isoformat() if document.published_at else None,
        "app_store_notice": (
            "Notify app stores BEFORE users continue if this is a significant change."
            if document.is_significant_change
            else None
        ),
    }


@router.get("/review-queue")
async def list_review_queue(
    _operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    limit: int = 50,
) -> dict[str, Any]:
    items = await ModerationService(session, clock).list_review_queue(limit=limit)
    return {"items": items}


@router.post("/review-queue/{item_id}/approve")
async def approve_review_item(
    item_id: UUID,
    payload: ApproveRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).approve_review_item(
        operator_identity=operator.identity,
        item_id=item_id,
        reason=payload.reason,
    )


@router.post("/review-queue/{item_id}/reject")
async def reject_review_item(
    item_id: UUID,
    payload: RejectReviewRequest,
    operator: OperatorPrincipal = Depends(require_moderation_operator),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> dict[str, Any]:
    return await ModerationService(session, clock).reject_review_item(
        operator_identity=operator.identity,
        item_id=item_id,
        reason=payload.reason,
        remove=payload.remove,
    )
