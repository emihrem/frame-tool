from pathlib import Path

import pytest
from PIL import Image

from frame_tool.colors import BLACK, WHITE
from frame_tool.exif import read_exif
from frame_tool.framer import apply_frame, render_preview
from frame_tool.models import (
    BorderConfig,
    ExifData,
    MetadataConfig,
    MetadataPosition,
)
from tests.conftest import JpgFactory

pytestmark = pytest.mark.integration


class TestApplyFrame:
    def test_dimensions_are_input_plus_borders(
        self, jpg_factory: JpgFactory, tmp_path: Path
    ) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"
        border = BorderConfig(top=30, bottom=120, left=40, right=20)

        apply_frame(src, dst, border, MetadataConfig(enabled=False), ExifData())

        with Image.open(dst) as out:
            assert out.size == (800 + 40 + 20, 600 + 30 + 120)

    def test_preserves_exif(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(aperture=2.0, iso=100, focal=85.0)
        dst = tmp_path / "out.jpg"

        apply_frame(src, dst, BorderConfig(), MetadataConfig(), read_exif(src))

        out_exif = read_exif(dst)
        assert out_exif.aperture == 2.0
        assert out_exif.iso == 100
        assert out_exif.focal_length == 85.0

    @pytest.mark.parametrize(
        ("color", "expected"),
        [(WHITE, (255, 255, 255)), (BLACK, (0, 0, 0))],
    )
    def test_border_color_applied(
        self,
        jpg_factory: JpgFactory,
        tmp_path: Path,
        color: str,
        expected: tuple[int, int, int],
    ) -> None:
        src = jpg_factory()
        dst = tmp_path / "out.jpg"

        apply_frame(src, dst, BorderConfig(color=color), MetadataConfig(enabled=False), ExifData())

        with Image.open(dst) as out:
            assert out.convert("RGB").getpixel((5, 5)) == expected

    def test_custom_hex_color(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory()
        dst = tmp_path / "out.jpg"
        cream = "#F5F5DC"

        apply_frame(src, dst, BorderConfig(color=cream), MetadataConfig(enabled=False), ExifData())

        with Image.open(dst) as out:
            r, g, b = out.convert("RGB").getpixel((5, 5))
            # JPEG chroma subsampling drifts by ±1 even on solid color blocks.
            assert abs(r - 245) <= 2
            assert abs(g - 245) <= 2
            assert abs(b - 220) <= 2

    def test_original_image_preserved_in_center(
        self, jpg_factory: JpgFactory, tmp_path: Path
    ) -> None:
        src = jpg_factory(color=(50, 100, 200))
        dst = tmp_path / "out.jpg"

        apply_frame(src, dst, BorderConfig(), MetadataConfig(enabled=False), ExifData())

        with Image.open(dst) as out:
            r, g, b = out.convert("RGB").getpixel((out.size[0] // 2, out.size[1] // 2))
            assert abs(r - 50) < 5
            assert abs(g - 100) < 5
            assert abs(b - 200) < 5

    def test_metadata_renders_text(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"
        exif = ExifData(aperture=2.8, shutter_speed="1/250", iso=400)

        apply_frame(src, dst, BorderConfig(bottom=200), MetadataConfig(font_size=40), exif)

        with Image.open(dst) as out:
            rgb = out.convert("RGB")
            scan_y = rgb.size[1] - 100  # middle of bottom border
            non_white = sum(1 for x in range(rgb.size[0]) if max(rgb.getpixel((x, scan_y))) < 200)
            assert non_white > 50, "expected text pixels in bottom border"

    def test_no_text_when_disabled(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"
        exif = ExifData(aperture=2.8, shutter_speed="1/250", iso=400)

        apply_frame(src, dst, BorderConfig(bottom=200), MetadataConfig(enabled=False), exif)

        with Image.open(dst) as out:
            rgb = out.convert("RGB")
            scan_y = rgb.size[1] - 100
            non_white = sum(1 for x in range(rgb.size[0]) if max(rgb.getpixel((x, scan_y))) < 200)
            assert non_white == 0

    def test_creates_parent_dirs(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        src = jpg_factory()
        dst = tmp_path / "a" / "b" / "c" / "out.jpg"

        apply_frame(src, dst, BorderConfig(), MetadataConfig(enabled=False), ExifData())

        assert dst.exists()

    @pytest.mark.parametrize("position", list(MetadataPosition))
    def test_all_positions_render(
        self, jpg_factory: JpgFactory, tmp_path: Path, position: MetadataPosition
    ) -> None:
        src = jpg_factory(size=(800, 600))
        dst = tmp_path / "out.jpg"
        exif = ExifData(aperture=2.8, shutter_speed="1/250", iso=400)

        apply_frame(
            src,
            dst,
            BorderConfig(top=120, bottom=200),
            MetadataConfig(position=position, font_size=30),
            exif,
        )

        assert dst.exists() and dst.stat().st_size > 0


class TestRenderPreview:
    def test_thumbnail_smaller_than_max(self, jpg_factory: JpgFactory) -> None:
        src = jpg_factory(size=(3000, 2000))
        preview = render_preview(src, BorderConfig(), MetadataConfig(), ExifData(), max_dim=800)
        assert max(preview.size) <= 800 + max(
            BorderConfig().left + BorderConfig().right, BorderConfig().top + BorderConfig().bottom
        )

    def test_small_image_not_upscaled(self, jpg_factory: JpgFactory) -> None:
        src = jpg_factory(size=(400, 300))
        preview = render_preview(src, BorderConfig(), MetadataConfig(), ExifData(), max_dim=1400)
        # Original is 400x300, with default borders 50/200/50/50 → 500x550
        assert preview.size == (500, 550)
