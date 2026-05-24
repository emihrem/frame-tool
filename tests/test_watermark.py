"""Tests for the PNG watermark overlay."""

from pathlib import Path

import pytest
from PIL import Image

from frame_tool.colors import WHITE
from frame_tool.framer import apply_frame
from frame_tool.models import (
    BorderConfig,
    ExifData,
    MetadataConfig,
    WatermarkConfig,
    WatermarkPosition,
)
from tests.conftest import JpgFactory

pytestmark = pytest.mark.integration


@pytest.fixture
def watermark_png(tmp_path: Path) -> Path:
    """A 200x80 solid red PNG with full alpha — easy to detect on a white border."""
    path = tmp_path / "wm.png"
    Image.new("RGBA", (200, 80), (255, 0, 0, 255)).save(path)
    return path


class TestWatermarkConfig:
    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="not found"):
            WatermarkConfig(path=tmp_path / "nope.png")

    def test_none_path_ok(self) -> None:
        cfg = WatermarkConfig()
        assert cfg.path is None

    def test_opacity_bounds(self, watermark_png: Path) -> None:
        with pytest.raises(ValueError, match="opacity"):
            WatermarkConfig(path=watermark_png, opacity=1.5)
        with pytest.raises(ValueError, match="opacity"):
            WatermarkConfig(path=watermark_png, opacity=-0.1)


class TestApplyWatermark:
    def test_disabled_by_default(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"

        apply_frame(
            src,
            dst,
            BorderConfig(color=WHITE),
            MetadataConfig(enabled=False),
            ExifData(),
            None,
            None,
            WatermarkConfig(),  # path=None
        )

        with Image.open(dst) as img:
            # No red anywhere — just original blue + white border
            rgb = img.convert("RGB")
            red_count = sum(
                1
                for y in range(rgb.size[1])
                for x in range(rgb.size[0])
                if rgb.getpixel((x, y))[0] > 200 and rgb.getpixel((x, y))[1] < 50
            )
            assert red_count == 0

    def test_renders_in_bottom_right(
        self, jpg_factory: JpgFactory, tmp_path: Path, watermark_png: Path
    ) -> None:
        src = jpg_factory(size=(1000, 800))
        dst = tmp_path / "out.jpg"

        apply_frame(
            src,
            dst,
            BorderConfig(top=20, bottom=120, left=20, right=20, color=WHITE),
            MetadataConfig(enabled=False),
            ExifData(),
            None,
            None,
            WatermarkConfig(
                path=watermark_png,
                position=WatermarkPosition.BOTTOM_RIGHT,
                size_ratio=0.2,
                margin=10,
            ),
        )

        with Image.open(dst) as img:
            rgb = img.convert("RGB")
            # Watermark should be in bottom-right quadrant
            w, h = rgb.size
            br_reds = sum(
                1
                for y in range(h // 2, h)
                for x in range(w // 2, w)
                if rgb.getpixel((x, y))[0] > 200 and rgb.getpixel((x, y))[1] < 50
            )
            tl_reds = sum(
                1
                for y in range(h // 2)
                for x in range(w // 2)
                if rgb.getpixel((x, y))[0] > 200 and rgb.getpixel((x, y))[1] < 50
            )
            assert br_reds > 1000, "expected substantial red watermark in bottom-right"
            assert tl_reds == 0, "watermark should not bleed to top-left"

    def test_opacity_reduces_redness(
        self, jpg_factory: JpgFactory, tmp_path: Path, watermark_png: Path
    ) -> None:
        # Half-opacity over white should yield pinkish, not pure red
        src = jpg_factory(size=(1000, 800))
        dst = tmp_path / "out.jpg"

        apply_frame(
            src,
            dst,
            BorderConfig(top=20, bottom=120, left=20, right=20, color=WHITE),
            MetadataConfig(enabled=False),
            ExifData(),
            None,
            None,
            WatermarkConfig(path=watermark_png, opacity=0.5, size_ratio=0.2, margin=10),
        )

        with Image.open(dst) as img:
            rgb = img.convert("RGB")
            w, h = rgb.size
            # Sample inside watermark area (near bottom-right, accounting for border)
            sample = rgb.getpixel((w - 60, h - 80))
            r, g, _b = sample
            # ~50% red over white → roughly (255, 128, 128)
            assert r > 200, "watermark area should still be reddish"
            assert g > 80 and g < 180, "green channel should be elevated by white blend"

    def test_size_ratio_scales_logo(
        self, jpg_factory: JpgFactory, tmp_path: Path, watermark_png: Path
    ) -> None:
        src = jpg_factory(size=(1000, 800))
        dst_small = tmp_path / "small.jpg"
        dst_big = tmp_path / "big.jpg"

        for dst, ratio in ((dst_small, 0.05), (dst_big, 0.3)):
            apply_frame(
                src,
                dst,
                BorderConfig(color=WHITE),
                MetadataConfig(enabled=False),
                ExifData(),
                None,
                None,
                WatermarkConfig(path=watermark_png, size_ratio=ratio, margin=10),
            )

        def count_red(p: Path) -> int:
            with Image.open(p) as img:
                rgb = img.convert("RGB")
                return sum(
                    1
                    for y in range(rgb.size[1])
                    for x in range(rgb.size[0])
                    if rgb.getpixel((x, y))[0] > 200 and rgb.getpixel((x, y))[1] < 50
                )

        assert count_red(dst_big) > 5 * count_red(dst_small)
