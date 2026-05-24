from importlib.resources import files
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from frame_tool.models import (
    BorderConfig,
    ExifData,
    MetadataConfig,
    MetadataPosition,
)

_FONT_RESOURCE = files("frame_tool").joinpath("assets/fonts/Inter-Regular.ttf")


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        with _FONT_RESOURCE.open("rb") as fh:
            data = fh.read()
        return ImageFont.truetype(BytesIO(data), size=size)
    except (FileNotFoundError, OSError):
        return ImageFont.load_default(size=size)


def _text_anchor_xy(
    position: MetadataPosition,
    canvas_size: tuple[int, int],
    border: BorderConfig,
    margin: int,
) -> tuple[tuple[int, int], str]:
    width, height = canvas_size
    if position is MetadataPosition.BOTTOM_CENTER:
        return (width // 2, height - border.bottom // 2), "mm"
    if position is MetadataPosition.BOTTOM_LEFT:
        return (border.left + margin, height - border.bottom // 2), "lm"
    if position is MetadataPosition.BOTTOM_RIGHT:
        return (width - border.right - margin, height - border.bottom // 2), "rm"
    if position is MetadataPosition.TOP_CENTER:
        return (width // 2, border.top // 2), "mm"
    if position is MetadataPosition.TOP_LEFT:
        return (border.left + margin, border.top // 2), "lm"
    return (width - border.right - margin, border.top // 2), "rm"


def _draw_metadata(
    canvas: Image.Image,
    border: BorderConfig,
    metadata: MetadataConfig,
    exif: ExifData,
) -> None:
    text = exif.format(metadata)
    if not text:
        return
    font = _load_font(metadata.font_size)
    draw = ImageDraw.Draw(canvas)
    xy, anchor = _text_anchor_xy(metadata.position, canvas.size, border, metadata.margin)
    draw.text(xy, text, font=font, fill=border.color.contrast_rgb, anchor=anchor)


def _frame_image(
    image: Image.Image,
    border: BorderConfig,
    metadata: MetadataConfig,
    exif: ExifData,
) -> Image.Image:
    canvas = ImageOps.expand(
        image,
        border=(border.left, border.top, border.right, border.bottom),
        fill=border.color.rgb,
    )
    if metadata.enabled:
        _draw_metadata(canvas, border, metadata, exif)
    return canvas


def apply_frame(
    image_path: Path,
    output_path: Path,
    border: BorderConfig,
    metadata: MetadataConfig,
    exif: ExifData,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as original:
        original.load()
        exif_bytes = original.info.get("exif")
        icc = original.info.get("icc_profile")
        framed = _frame_image(original, border, metadata, exif)

    save_kwargs: dict[str, Any] = {
        "quality": "keep",
        "subsampling": "keep",
        "optimize": True,
    }
    if exif_bytes:
        save_kwargs["exif"] = exif_bytes
    if icc:
        save_kwargs["icc_profile"] = icc

    try:
        framed.save(output_path, format="JPEG", **save_kwargs)
    except (ValueError, OSError):
        save_kwargs["quality"] = 95
        save_kwargs.pop("subsampling", None)
        framed.save(output_path, format="JPEG", **save_kwargs)


def render_preview(
    image_path: Path,
    border: BorderConfig,
    metadata: MetadataConfig,
    exif: ExifData,
    max_dim: int = 1400,
) -> Image.Image:
    with Image.open(image_path) as original:
        original.load()
        scale = min(1.0, max_dim / max(original.size))
        if scale < 1.0:
            new_size = (round(original.size[0] * scale), round(original.size[1] * scale))
            thumb = original.resize(new_size, Image.Resampling.LANCZOS)
        else:
            thumb = original.copy()

    scaled_border = border.scaled(scale)
    scaled_metadata = metadata.model_copy(
        update={
            "font_size": max(8, round(metadata.font_size * scale)),
            "margin": max(0, round(metadata.margin * scale)),
        }
    )
    return _frame_image(thumb, scaled_border, scaled_metadata, exif)
