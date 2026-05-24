"""Tests for the Instagram aspect-ratio padding feature."""

from pathlib import Path

import pytest
from PIL import Image

from frame_tool.colors import BLACK, WHITE
from frame_tool.framer import _pad_to_ratio, apply_frame
from frame_tool.models import (
    BorderConfig,
    ExifData,
    InstagramConfig,
    InstagramPreset,
    MetadataConfig,
)
from tests.conftest import JpgFactory


class TestInstagramPreset:
    @pytest.mark.parametrize(
        ("preset", "expected"),
        [
            (InstagramPreset.SQUARE, 1.0),
            (InstagramPreset.PORTRAIT, 0.8),
            (InstagramPreset.LANDSCAPE, 1.91),
            (InstagramPreset.STORY, 9 / 16),
            (InstagramPreset.NONE, None),
            (InstagramPreset.AUTO, None),
        ],
    )
    def test_ratio(self, preset: InstagramPreset, expected: float | None) -> None:
        assert preset.ratio == expected

    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            ((1600, 900), InstagramPreset.LANDSCAPE),
            ((900, 1600), InstagramPreset.PORTRAIT),
            ((1000, 1000), InstagramPreset.SQUARE),
        ],
    )
    def test_auto_resolves(self, size: tuple[int, int], expected: InstagramPreset) -> None:
        assert InstagramPreset.AUTO.resolve(size) is expected

    def test_concrete_preset_resolve_is_noop(self) -> None:
        assert InstagramPreset.SQUARE.resolve((100, 200)) is InstagramPreset.SQUARE


class TestPadToRatio:
    def test_already_correct_returns_same(self) -> None:
        img = Image.new("RGB", (1000, 1000), (255, 255, 255))
        out = _pad_to_ratio(img, 1.0, (0, 0, 0))
        assert out.size == img.size

    def test_pad_vertically_when_too_wide(self) -> None:
        # Wide landscape, target 1:1 → add vertical bars
        img = Image.new("RGB", (1000, 500), (200, 200, 200))
        out = _pad_to_ratio(img, 1.0, (0, 0, 0))
        assert out.size == (1000, 1000)
        # Top bar should be the fill color
        assert out.convert("RGB").getpixel((500, 50)) == (0, 0, 0)
        # Center should still be original
        assert out.convert("RGB").getpixel((500, 500)) == (200, 200, 200)

    def test_pad_horizontally_when_too_tall(self) -> None:
        # Tall portrait, target 1:1 → add horizontal bars
        img = Image.new("RGB", (500, 1000), (200, 200, 200))
        out = _pad_to_ratio(img, 1.0, (255, 255, 255))
        assert out.size == (1000, 1000)
        # Left bar should be fill
        assert out.convert("RGB").getpixel((50, 500)) == (255, 255, 255)
        # Center should still be original
        assert out.convert("RGB").getpixel((500, 500)) == (200, 200, 200)

    def test_pad_to_4_5(self) -> None:
        # Original 3:2 (1500x1000), target 4:5 (0.8) → tall canvas
        img = Image.new("RGB", (1500, 1000), (100, 100, 100))
        out = _pad_to_ratio(img, 4 / 5, (255, 255, 255))
        # width=1500, so height should be 1500/0.8 = 1875
        assert out.size == (1500, 1875)


class TestApplyFrameInstagram:
    def test_no_op_when_preset_is_none(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"
        apply_frame(
            src,
            dst,
            BorderConfig(top=10, bottom=10, left=10, right=10),
            MetadataConfig(enabled=False),
            ExifData(),
            InstagramConfig(preset=InstagramPreset.NONE),
        )
        with Image.open(dst) as out:
            assert out.size == (820, 620)  # only the user-defined border

    def test_pads_to_square(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(1600, 900))
        dst = tmp_path / "out.jpg"
        apply_frame(
            src,
            dst,
            BorderConfig(top=0, bottom=0, left=0, right=0, color=WHITE),
            MetadataConfig(enabled=False),
            ExifData(),
            InstagramConfig(preset=InstagramPreset.SQUARE),
        )
        with Image.open(dst) as out:
            assert out.size == (1600, 1600)

    def test_pads_to_portrait(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(1500, 1000))  # 3:2
        dst = tmp_path / "out.jpg"
        apply_frame(
            src,
            dst,
            BorderConfig(top=0, bottom=0, left=0, right=0),
            MetadataConfig(enabled=False),
            ExifData(),
            InstagramConfig(preset=InstagramPreset.PORTRAIT),
        )
        with Image.open(dst) as out:
            assert out.size == (1500, 1875)  # 1500 / (4/5)

    def test_auto_picks_landscape_for_horizontal(
        self, jpg_factory: JpgFactory, tmp_path: Path
    ) -> None:
        src = jpg_factory(size=(1600, 900))
        dst = tmp_path / "out.jpg"
        apply_frame(
            src,
            dst,
            BorderConfig(top=0, bottom=0, left=0, right=0),
            MetadataConfig(enabled=False),
            ExifData(),
            InstagramConfig(preset=InstagramPreset.AUTO),
        )
        with Image.open(dst) as out:
            # 1600 width, target 1.91 → height = 1600/1.91 ≈ 838
            # Image is already 900 height which is taller than 838,
            # so it pads horizontally instead. Width = 900 * 1.91 = 1719
            assert out.size == (1719, 900)

    def test_auto_picks_portrait_for_vertical(
        self, jpg_factory: JpgFactory, tmp_path: Path
    ) -> None:
        src = jpg_factory(size=(900, 1600))
        dst = tmp_path / "out.jpg"
        apply_frame(
            src,
            dst,
            BorderConfig(top=0, bottom=0, left=0, right=0),
            MetadataConfig(enabled=False),
            ExifData(),
            InstagramConfig(preset=InstagramPreset.AUTO),
        )
        with Image.open(dst) as out:
            # 900x1600 → 4:5 → width should grow to 1600 * 0.8 = 1280
            assert out.size == (1280, 1600)

    def test_downscale_to_1080(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(3000, 2000))
        dst = tmp_path / "out.jpg"
        apply_frame(
            src,
            dst,
            BorderConfig(top=0, bottom=0, left=0, right=0),
            MetadataConfig(enabled=False),
            ExifData(),
            InstagramConfig(preset=InstagramPreset.SQUARE, downscale_to=1080),
        )
        with Image.open(dst) as out:
            assert max(out.size) == 1080
            assert out.size == (1080, 1080)

    def test_no_downscale_preserves_resolution(
        self, jpg_factory: JpgFactory, tmp_path: Path
    ) -> None:
        src = jpg_factory(size=(3000, 2000))
        dst = tmp_path / "out.jpg"
        apply_frame(
            src,
            dst,
            BorderConfig(top=0, bottom=0, left=0, right=0),
            MetadataConfig(enabled=False),
            ExifData(),
            InstagramConfig(preset=InstagramPreset.SQUARE),
        )
        with Image.open(dst) as out:
            assert out.size == (3000, 3000)  # padded to square, no downscale

    def test_padding_color_matches_border(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(1600, 900), color=(255, 0, 0))
        dst = tmp_path / "out.jpg"
        apply_frame(
            src,
            dst,
            BorderConfig(top=0, bottom=0, left=0, right=0, color=BLACK),
            MetadataConfig(enabled=False),
            ExifData(),
            InstagramConfig(preset=InstagramPreset.SQUARE),
        )
        with Image.open(dst) as out:
            rgb = out.convert("RGB")
            # Top padding should be black
            r, g, b = rgb.getpixel((800, 100))
            assert r < 20 and g < 20 and b < 20
