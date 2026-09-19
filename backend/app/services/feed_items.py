"""Shared feed-item projection helpers."""

from __future__ import annotations

from datetime import datetime

from app.creative_types import MediaUrls, get_creative_type_registry
from app.creative_types.base import truncate_preview
from app.models.user import User
from app.repositories.publications import FeedRow
from app.schemas.feed import FeedItem
from app.schemas.feed_shared import FeedPromptSummary, FeedUserSummary
from app.schemas.submissions import CreativeTypeSchema, timer_fields
from app.services.media_urls import signed_display_url, signed_thumbnail_url
from app.storage.base import StorageAdapter

CAPTION_PREVIEW_MAX_LENGTH = 140


def caption_preview(caption: str | None) -> str | None:
    """Truncate a caption for feed/profile display."""
    return truncate_preview(caption, CAPTION_PREVIEW_MAX_LENGTH)


async def build_feed_item(
    *,
    row: FeedRow,
    viewer: User | None,
    storage: StorageAdapter,
    expires_at: datetime,
    viewer_has_liked: bool,
    avatar_url: str | None = None,
) -> FeedItem:
    """Build a FeedItem from a joined feed/profile row."""
    media = MediaUrls()
    if row.upload is not None:
        media = MediaUrls(
            image_url=await signed_display_url(
                storage=storage,
                original_key=row.upload.storage_key,
                expires_at=expires_at,
            ),
            thumbnail_url=await signed_thumbnail_url(
                storage=storage,
                original_key=row.upload.storage_key,
                expires_at=expires_at,
            ),
        )

    timer_mode, timer_seconds = timer_fields(row.session)
    is_owner = viewer is not None and viewer.id == row.publication.user_id
    definition = get_creative_type_registry().get(row.publication.creative_type)
    content = definition.handler.project(
        content=row.publication.content or {},
        media=media,
        is_owner=is_owner,
        preview=True,
    )

    return FeedItem(
        id=row.publication.id,
        creative_type=CreativeTypeSchema(row.publication.creative_type.value),
        caption_preview=caption_preview(row.publication.caption),
        content=content,
        user=FeedUserSummary(
            id=row.user.id,
            username=row.user.username or "",
            display_name=row.user.display_name,
            avatar_url=avatar_url,
        ),
        prompt=FeedPromptSummary(
            id=row.prompt.id,
            prompt_date=row.prompt.prompt_date,
            word_1=row.prompt.word_1,
            word_2=row.prompt.word_2,
            word_3=row.prompt.word_3,
        ),
        timer_mode=timer_mode,
        timer_seconds=timer_seconds,
        like_count=row.publication.like_count,
        reflection_count=row.publication.reflection_count,
        viewer_has_liked=viewer_has_liked,
        is_owner=is_owner,
        published_at=row.publication.published_at,
    )
