"""Tests for the free-text caption rendered in the border."""

from pathlib import Path

import pytest
from PIL import Image

from frame_tool.colors import BLACK, WHITE
from frame_tool.framer import apply_frame
from frame_tool.models import (
    BorderConfig,
    CaptionConfig,
    ExifData,
    MetadataConfig,
    MetadataPosition,
)
from tests.conftest import JpgFactory

pytestmark = pytest.mark.integration


def _count_non_bg_in_box(
    path: Path,
    bg: tuple[int, int, int],
    *,
    y_range: tuple[int, int],
    x_range: tuple[int, int] | None = None,
) -> int:
    """Count pixels in a sub-region that differ noticeably from the background."""
    with Image.open(path) as img:
        rgb = img.convert("RGB")
    x_lo, x_hi = x_range if x_range else (0, rgb.size[0])
    return sum(
        1
        for y in range(*y_range)
        for x in range(x_lo, x_hi)
        if any(abs(rgb.getpixel((x, y))[i] - bg[i]) > 30 for i in range(3))
    )


_BOTTOM_BORDER_RANGE = (700, 800)  # default top=50 + image 600 = 650; bottom band 650-850


class TestCaption:
    def test_empty_text_renders_nothing(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"

        apply_frame(
            src,
            dst,
            BorderConfig(bottom=200),
            MetadataConfig(enabled=False),
            ExifData(),
            None,
            CaptionConfig(text=""),
        )

        assert _count_non_bg_in_box(dst, (255, 255, 255), y_range=_BOTTOM_BORDER_RANGE) == 0

    def test_caption_renders_text(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"

        apply_frame(
            src,
            dst,
            BorderConfig(bottom=200, color=WHITE),
            MetadataConfig(enabled=False),
            ExifData(),
            None,
            CaptionConfig(text="© 2026 Emi Mer", font_size=40),
        )

        non_white = _count_non_bg_in_box(dst, (255, 255, 255), y_range=_BOTTOM_BORDER_RANGE)
        assert non_white > 200, "expected caption pixels in bottom border"

    def test_caption_contrasts_with_black_border(
        self, jpg_factory: JpgFactory, tmp_path: Path
    ) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"

        apply_frame(
            src,
            dst,
            BorderConfig(bottom=200, color=BLACK),
            MetadataConfig(enabled=False),
            ExifData(),
            None,
            CaptionConfig(text="Bariloche · 2026", font_size=40),
        )

        non_black = _count_non_bg_in_box(dst, (0, 0, 0), y_range=_BOTTOM_BORDER_RANGE)
        assert non_black > 200, "expected light caption pixels on black border"

    def test_caption_and_exif_coexist(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"
        exif = ExifData(aperture=2.8, shutter_speed="1/250", iso=400)

        apply_frame(
            src,
            dst,
            BorderConfig(bottom=200),
            MetadataConfig(position=MetadataPosition.BOTTOM_RIGHT, font_size=32),
            exif,
            None,
            CaptionConfig(text="© Emi", position=MetadataPosition.BOTTOM_LEFT, font_size=32),
        )

        left = _count_non_bg_in_box(
            dst, (255, 255, 255), y_range=_BOTTOM_BORDER_RANGE, x_range=(0, 400)
        )
        right = _count_non_bg_in_box(
            dst, (255, 255, 255), y_range=_BOTTOM_BORDER_RANGE, x_range=(400, 800)
        )
        assert left > 50, "caption missing on left"
        assert right > 50, "EXIF missing on right"
