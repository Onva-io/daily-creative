"""Policy document and acceptance repositories."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import PolicyAcceptance, PolicyDocument, PolicyKind, PolicyStatus


class PolicyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, document_id: uuid.UUID) -> PolicyDocument | None:
        return await self._session.get(PolicyDocument, document_id)

    async def get_by_kind_and_version(
        self,
        kind: PolicyKind,
        version: str,
    ) -> PolicyDocument | None:
        result = await self._session.execute(
            select(PolicyDocument).where(
                PolicyDocument.kind == kind,
                PolicyDocument.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def list_published(self) -> list[PolicyDocument]:
        result = await self._session.execute(
            select(PolicyDocument)
            .where(PolicyDocument.status == PolicyStatus.published)
            .order_by(PolicyDocument.kind.asc())
        )
        return list(result.scalars().all())

    async def get_published(self, kind: PolicyKind) -> PolicyDocument | None:
        result = await self._session.execute(
            select(PolicyDocument).where(
                PolicyDocument.kind == kind,
                PolicyDocument.status == PolicyStatus.published,
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self, *, kind: PolicyKind | None = None) -> list[PolicyDocument]:
        stmt = select(PolicyDocument).order_by(
            PolicyDocument.kind.asc(),
            PolicyDocument.created_at.desc(),
        )
        if kind is not None:
            stmt = stmt.where(PolicyDocument.kind == kind)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        *,
        kind: PolicyKind,
        version: str,
        title: str,
        body_markdown: str,
        content_hash: str,
        minimum_age: int = 13,
        is_significant_change: bool = False,
        change_summary: str | None = None,
        status: PolicyStatus = PolicyStatus.draft,
        commit: bool = True,
    ) -> PolicyDocument:
        row = PolicyDocument(
            id=uuid.uuid4(),
            kind=kind,
            version=version,
            title=title,
            body_markdown=body_markdown,
            content_hash=content_hash,
            minimum_age=minimum_age,
            status=status,
            is_significant_change=is_significant_change,
            change_summary=change_summary,
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
            await self._session.refresh(row)
        else:
            await self._session.flush()
        return row

    async def publish(
        self,
        document: PolicyDocument,
        *,
        published_at: datetime,
        commit: bool = False,
    ) -> PolicyDocument:
        current = await self.get_published(document.kind)
        if current is not None and current.id != document.id:
            current.status = PolicyStatus.superseded
        document.status = PolicyStatus.published
        document.published_at = published_at
        if commit:
            await self._session.commit()
            await self._session.refresh(document)
        else:
            await self._session.flush()
        return document


class PolicyAcceptanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user_document(
        self,
        *,
        user_id: uuid.UUID,
        policy_document_id: uuid.UUID,
    ) -> PolicyAcceptance | None:
        result = await self._session.execute(
            select(PolicyAcceptance).where(
                PolicyAcceptance.user_id == user_id,
                PolicyAcceptance.policy_document_id == policy_document_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[PolicyAcceptance]:
        result = await self._session.execute(
            select(PolicyAcceptance).where(PolicyAcceptance.user_id == user_id)
        )
        return list(result.scalars().all())

    async def accepted_document_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self._session.execute(
            select(PolicyAcceptance.policy_document_id).where(PolicyAcceptance.user_id == user_id)
        )
        return set(result.scalars().all())

    async def record(
        self,
        *,
        user_id: uuid.UUID,
        policy_document_id: uuid.UUID,
        accepted_at: datetime,
        app_version: str | None = None,
        platform: str | None = None,
        locale: str | None = None,
        commit: bool = True,
    ) -> PolicyAcceptance:
        existing = await self.get_for_user_document(
            user_id=user_id,
            policy_document_id=policy_document_id,
        )
        if existing is not None:
            return existing
        row = PolicyAcceptance(
            id=uuid.uuid4(),
            user_id=user_id,
            policy_document_id=policy_document_id,
            accepted_at=accepted_at,
            app_version=app_version,
            platform=platform,
            locale=locale,
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
            await self._session.refresh(row)
        else:
            await self._session.flush()
        return row
