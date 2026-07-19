"""Bounded synchronous image validation and derivative generation."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import AppError

DISPLAY_MAX_EDGE = 2048
THUMBNAIL_MAX_EDGE = 512
JPEG_QUALITY = 85


@dataclass(frozen=True, slots=True)
class ProcessedImage:
    """Validated original metadata plus derivative JPEG bytes."""

    width: int
    height: int
    content_type: str
    display_bytes: bytes
    thumbnail_bytes: bytes
    display_content_type: str = "image/jpeg"
    thumbnail_content_type: str = "image/jpeg"


def process_upload_image(*, data: bytes, declared_content_type: str) -> ProcessedImage:
    """Decode, strip EXIF, normalise orientation, and build derivatives."""
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            normalised = ImageOps.exif_transpose(image)
            if normalised is None:
                normalised = image
            rgb = _to_rgb(normalised)
            width, height = rgb.size
            if width < 1 or height < 1:
                raise AppError(
                    code="invalid_image",
                    message="The uploaded file is not a valid image.",
                    status_code=422,
                )
            display = _resize_max_edge(rgb, DISPLAY_MAX_EDGE)
            thumbnail = _resize_max_edge(rgb, THUMBNAIL_MAX_EDGE)
            return ProcessedImage(
                width=width,
                height=height,
                content_type=declared_content_type,
                display_bytes=_encode_jpeg(display),
                thumbnail_bytes=_encode_jpeg(thumbnail),
            )
    except AppError:
        raise
    except UnidentifiedImageError as exc:
        raise AppError(
            code="invalid_image",
            message="The uploaded file is not a valid image.",
            status_code=422,
        ) from exc
    except OSError as exc:
        raise AppError(
            code="invalid_image",
            message="The uploaded file is not a valid image.",
            status_code=422,
        ) from exc


def _to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in {"RGB", "L"}:
        return image.convert("RGB")
    if image.mode in {"RGBA", "LA", "P"}:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return image.convert("RGB")


def _resize_max_edge(image: Image.Image, max_edge: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_edge:
        return image.copy()
    scale = max_edge / float(longest)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _encode_jpeg(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue()
