from importlib.resources import files
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from frame_tool.models import (
    BorderColor,
    BorderConfig,
    ExifData,
    InstagramConfig,
    InstagramPreset,
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


def _pad_to_ratio(
    image: Image.Image, target_ratio: float, fill: tuple[int, int, int]
) -> Image.Image:
    """Pad ``image`` symmetrically until ``width/height == target_ratio``.

    Pads horizontally if the image is too narrow, vertically if too tall.
    Pixel data is never cropped or resampled.
    """
    width, height = image.size
    current = width / height
    if abs(current - target_ratio) < 1e-3:
        return image

    if current < target_ratio:
        new_width = round(height * target_ratio)
        extra = new_width - width
        left_pad = extra // 2
        right_pad = extra - left_pad
        return ImageOps.expand(image, border=(left_pad, 0, right_pad, 0), fill=fill)

    new_height = round(width / target_ratio)
    extra = new_height - height
    top_pad = extra // 2
    bottom_pad = extra - top_pad
    return ImageOps.expand(image, border=(0, top_pad, 0, bottom_pad), fill=fill)


def _downscale(image: Image.Image, max_long_edge: int) -> Image.Image:
    long_edge = max(image.size)
    if long_edge <= max_long_edge:
        return image
    scale = max_long_edge / long_edge
    new_size = (round(image.size[0] * scale), round(image.size[1] * scale))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _apply_instagram(
    image: Image.Image, instagram: InstagramConfig, color: BorderColor
) -> Image.Image:
    if instagram.preset is InstagramPreset.NONE:
        return image
    preset = instagram.preset.resolve(image.size)
    ratio = preset.ratio
    if ratio is None:
        return image
    padded = _pad_to_ratio(image, ratio, color.rgb)
    if instagram.downscale_to is not None:
        padded = _downscale(padded, instagram.downscale_to)
    return padded


def _frame_image(
    image: Image.Image,
    border: BorderConfig,
    metadata: MetadataConfig,
    exif: ExifData,
    instagram: InstagramConfig | None = None,
) -> Image.Image:
    canvas = ImageOps.expand(
        image,
        border=(border.left, border.top, border.right, border.bottom),
        fill=border.color.rgb,
    )
    if metadata.enabled:
        _draw_metadata(canvas, border, metadata, exif)
    if instagram is not None:
        canvas = _apply_instagram(canvas, instagram, border.color)
    return canvas


def apply_frame(
    image_path: Path,
    output_path: Path,
    border: BorderConfig,
    metadata: MetadataConfig,
    exif: ExifData,
    instagram: InstagramConfig | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as original:
        original.load()
        exif_bytes = original.info.get("exif")
        icc = original.info.get("icc_profile")
        framed = _frame_image(original, border, metadata, exif, instagram)

    keep_quality = instagram is None or instagram.downscale_to is None
    save_kwargs: dict[str, Any] = {
        "optimize": True,
    }
    if keep_quality:
        save_kwargs["quality"] = "keep"
        save_kwargs["subsampling"] = "keep"
    else:
        save_kwargs["quality"] = 95
        save_kwargs["subsampling"] = 0
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
    instagram: InstagramConfig | None = None,
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
    # Don't downscale the preview again to Instagram size — the GUI already
    # works with a thumbnail. Just pad to the target ratio.
    preview_instagram = (
        instagram.model_copy(update={"downscale_to": None}) if instagram is not None else None
    )
    return _frame_image(thumb, scaled_border, scaled_metadata, exif, preview_instagram)
