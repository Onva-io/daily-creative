"""Policy document application service."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date
from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, SystemClock
from app.core.errors import AppError
from app.models.moderation_action import ModerationActionType
from app.models.policy import PolicyDocument, PolicyKind, PolicyStatus
from app.models.report import ReportTargetType
from app.models.user import User
from app.observability.metrics import send_alert
from app.repositories.moderation_actions import ModerationActionRepository
from app.repositories.policies import PolicyAcceptanceRepository, PolicyDocumentRepository
from app.repositories.users import UserRepository
from app.schemas.policies import (
    AcceptPoliciesRequest,
    AcceptPoliciesResponse,
    AcceptedPolicyItem,
    ConsentState,
    CurrentPoliciesResponse,
    PolicyAcceptanceSummary,
    PolicyDocumentResponse,
    PolicyKindSchema,
    policy_kind_from_schema,
)
from app.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_MINIMUM_AGE = 13


def content_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def age_on(today: date, *, date_of_birth: date) -> int:
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


class PolicyService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        clock: Clock | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._documents = PolicyDocumentRepository(session)
        self._acceptances = PolicyAcceptanceRepository(session)
        self._users = UserRepository(session)
        self._actions = ModerationActionRepository(session)
        self._clock = clock or SystemClock()
        self._settings = settings or get_settings()

    async def current_policies(self) -> CurrentPoliciesResponse:
        documents = await self._documents.list_published()
        return CurrentPoliciesResponse(
            documents=[PolicyDocumentResponse.from_orm(doc) for doc in documents]
        )

    async def consent_state(self, user: User) -> ConsentState:
        published = await self._documents.list_published()
        accepted_ids = await self._acceptances.accepted_document_ids(user.id)
        acceptances = await self._acceptances.list_for_user(user.id)
        accepted_by_doc = {row.policy_document_id: row for row in acceptances}

        outstanding: list[PolicyKindSchema] = []
        accepted_summaries: list[PolicyAcceptanceSummary] = []
        for doc in published:
            if doc.id in accepted_ids:
                row = accepted_by_doc[doc.id]
                accepted_summaries.append(
                    PolicyAcceptanceSummary(
                        kind=PolicyKindSchema(doc.kind.value),
                        version=doc.version,
                        accepted_at=row.accepted_at,
                    )
                )
            else:
                outstanding.append(PolicyKindSchema(doc.kind.value))

        minimum_age = self._minimum_age_from(published)
        # Age is required once policies are published (public launch posture).
        age_required = user.date_of_birth is None and bool(published)
        if user.date_of_birth is not None and published:
            if age_on(self._clock.today(), date_of_birth=user.date_of_birth) < minimum_age:
                raise AppError(
                    code="under_minimum_age",
                    message=f"You must be at least {minimum_age} years old to use this app.",
                    status_code=403,
                    details={"minimum_age": minimum_age},
                )

        consent_required = bool(outstanding) or age_required
        return ConsentState(
            consent_required=consent_required,
            outstanding_kinds=outstanding,
            accepted=accepted_summaries,
            current_documents=[PolicyDocumentResponse.from_orm(doc) for doc in published],
            age_required=age_required,
            minimum_age=minimum_age,
        )

    async def require_consent(self, user: User) -> ConsentState:
        state = await self.consent_state(user)
        if state.consent_required:
            raise AppError(
                code="consent_required",
                message="Please review and accept the latest policies to continue.",
                status_code=403,
                details={
                    "outstanding_kinds": [kind.value for kind in state.outstanding_kinds],
                    "age_required": state.age_required,
                    "minimum_age": state.minimum_age,
                },
            )
        return state

    async def accept(
        self,
        user: User,
        payload: AcceptPoliciesRequest,
    ) -> AcceptPoliciesResponse:
        published = {doc.kind: doc for doc in await self._documents.list_published()}
        now = self._clock.now()
        accepted: list[AcceptedPolicyItem] = []

        for item in payload.documents:
            kind = policy_kind_from_schema(item.kind)
            current = published.get(kind)
            if current is None:
                raise AppError(
                    code="policy_not_found",
                    message=f"No published {kind.value} document is available.",
                    status_code=404,
                )
            if current.version != item.version:
                raise AppError(
                    code="policy_version_stale",
                    message="A newer version of this policy is available. Please review it again.",
                    status_code=409,
                    details={
                        "kind": kind.value,
                        "requested_version": item.version,
                        "current_version": current.version,
                    },
                )
            row = await self._acceptances.record(
                user_id=user.id,
                policy_document_id=current.id,
                accepted_at=now,
                app_version=payload.app_version,
                platform=payload.platform,
                locale=payload.locale,
                commit=False,
            )
            accepted.append(
                AcceptedPolicyItem(
                    kind=PolicyKindSchema(kind.value),
                    version=current.version,
                    accepted_at=row.accepted_at,
                )
            )

        await self._session.commit()
        return AcceptPoliciesResponse(accepted=accepted)

    async def set_date_of_birth(self, user: User, *, date_of_birth: date) -> User:
        if date_of_birth > self._clock.today():
            raise AppError(
                code="date_of_birth_invalid",
                message="Date of birth cannot be in the future.",
                status_code=422,
            )
        published = await self._documents.list_published()
        minimum_age = self._minimum_age_from(published)
        if age_on(self._clock.today(), date_of_birth=date_of_birth) < minimum_age:
            raise AppError(
                code="under_minimum_age",
                message=f"You must be at least {minimum_age} years old to use this app.",
                status_code=403,
                details={"minimum_age": minimum_age},
            )
        user.date_of_birth = date_of_birth
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def create_draft(
        self,
        *,
        kind: PolicyKind,
        version: str,
        title: str,
        body_markdown: str,
        minimum_age: int = DEFAULT_MINIMUM_AGE,
        is_significant_change: bool = False,
        change_summary: str | None = None,
        operator_identity: str,
    ) -> PolicyDocument:
        existing = await self._documents.get_by_kind_and_version(kind, version)
        if existing is not None:
            if existing.status != PolicyStatus.draft:
                raise AppError(
                    code="policy_version_immutable",
                    message="Published policy versions cannot be modified.",
                    status_code=409,
                )
            existing.title = title
            existing.body_markdown = body_markdown
            existing.content_hash = content_hash(body_markdown)
            existing.minimum_age = minimum_age
            existing.is_significant_change = is_significant_change
            existing.change_summary = change_summary
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        document = await self._documents.create(
            kind=kind,
            version=version,
            title=title,
            body_markdown=body_markdown,
            content_hash=content_hash(body_markdown),
            minimum_age=minimum_age,
            is_significant_change=is_significant_change,
            change_summary=change_summary,
            commit=True,
        )
        _ = operator_identity
        return document

    async def publish(
        self,
        document_id: uuid.UUID,
        *,
        operator_identity: str,
    ) -> PolicyDocument:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise AppError(
                code="policy_not_found",
                message="Policy document not found.",
                status_code=404,
            )
        if document.status == PolicyStatus.published:
            return document
        if document.status != PolicyStatus.draft:
            raise AppError(
                code="policy_not_draft",
                message="Only draft documents can be published.",
                status_code=409,
            )

        if document.is_significant_change:
            logger.warning(
                "significant_policy_change_publishing",
                extra={
                    "kind": document.kind.value,
                    "version": document.version,
                    "change_summary": document.change_summary,
                },
            )
            await send_alert(
                self._settings,
                title="Significant policy change publishing",
                detail=(
                    f"{document.kind.value} v{document.version} marked significant. "
                    f"Notify app stores BEFORE users continue. "
                    f"Summary: {document.change_summary or '(none)'}"
                ),
            )

        published = await self._documents.publish(
            document,
            published_at=self._clock.now(),
            commit=False,
        )
        await self._actions.record(
            operator_identity=operator_identity,
            action=ModerationActionType.publish_policy,
            target_type=ReportTargetType.profile,
            target_id=document.id,
            reason=f"Published {document.kind.value} v{document.version}",
            commit=False,
        )
        await self._session.commit()
        await self._session.refresh(published)
        return published

    async def list_documents(self, *, kind: PolicyKind | None = None) -> list[PolicyDocument]:
        return await self._documents.list_all(kind=kind)

    async def render_html(self, kind: PolicyKind) -> str:
        document = await self._documents.get_published(kind)
        if document is None:
            raise AppError(
                code="policy_not_found",
                message="No published document is available.",
                status_code=404,
            )
        body = escape(document.body_markdown).replace("\n", "<br>\n")
        return (
            "<!DOCTYPE html><html><head>"
            f"<meta charset='utf-8'><title>{escape(document.title)}</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
            "max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5}</style>"
            f"</head><body><h1>{escape(document.title)}</h1>"
            f"<p><small>Version {escape(document.version)}</small></p>"
            f"<div>{body}</div></body></html>"
        )

    @staticmethod
    def _minimum_age_from(documents: list[PolicyDocument]) -> int:
        ages = [doc.minimum_age for doc in documents if doc.kind == PolicyKind.terms]
        if ages:
            return max(ages)
        if documents:
            return max(doc.minimum_age for doc in documents)
        return DEFAULT_MINIMUM_AGE
