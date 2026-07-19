"""Upload repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload import DerivativeStatus, Upload, UploadPurpose, UploadStatus


class UploadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        purpose: UploadPurpose,
        storage_bucket: str,
        storage_key: str,
        content_type: str,
        expires_at: datetime,
        upload_id: uuid.UUID | None = None,
    ) -> Upload:
        upload = Upload(
            id=upload_id or uuid.uuid4(),
            user_id=user_id,
            purpose=purpose,
            status=UploadStatus.pending,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            content_type=content_type,
            expires_at=expires_at,
        )
        self._session.add(upload)
        await self._session.commit()
        await self._session.refresh(upload)
        return upload

    async def get_by_id(self, upload_id: uuid.UUID) -> Upload | None:
        result = await self._session.execute(select(Upload).where(Upload.id == upload_id))
        return result.scalar_one_or_none()

    async def get_by_ids(self, upload_ids: list[uuid.UUID]) -> dict[uuid.UUID, Upload]:
        if not upload_ids:
            return {}
        result = await self._session.execute(select(Upload).where(Upload.id.in_(upload_ids)))
        return {upload.id: upload for upload in result.scalars().all()}

    async def save(self, upload: Upload) -> Upload:
        await self._session.commit()
        await self._session.refresh(upload)
        return upload

    async def mark_ready(
        self,
        upload: Upload,
        *,
        byte_size: int,
        width: int,
        height: int,
        checksum: str | None,
        uploaded_at: datetime,
        verified_at: datetime,
    ) -> Upload:
        upload.status = UploadStatus.ready
        upload.byte_size = byte_size
        upload.width = width
        upload.height = height
        upload.checksum = checksum
        upload.uploaded_at = uploaded_at
        upload.verified_at = verified_at
        upload.derivative_status = DerivativeStatus.ready
        return await self.save(upload)

    async def mark_consumed(
        self,
        upload: Upload,
        *,
        consumed_at: datetime,
        commit: bool = True,
    ) -> Upload:
        upload.status = UploadStatus.consumed
        upload.consumed_at = consumed_at
        if commit:
            return await self.save(upload)
        await self._session.flush()
        return upload
