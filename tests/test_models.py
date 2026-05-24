from importlib.resources import files
from pathlib import Path

import pytest
from pydantic import ValidationError

from frame_tool.colors import BLACK, WHITE
from frame_tool.models import (
    BorderConfig,
    ExifData,
    FontFamily,
    FrameJob,
    MetadataConfig,
    MetadataPosition,
)


class TestBorderConfig:
    def test_defaults(self) -> None:
        cfg = BorderConfig()
        assert cfg.top == 50
        assert cfg.bottom == 200
        assert cfg.left == 50
        assert cfg.right == 50
        assert cfg.color == WHITE

    def test_accepts_named_color(self) -> None:
        cfg = BorderConfig(color="cream")
        assert cfg.color == "#F5F5DC"

    def test_accepts_hex(self) -> None:
        cfg = BorderConfig(color="#FF8800")
        assert cfg.color == "#FF8800"

    def test_rejects_garbage(self) -> None:
        with pytest.raises(ValidationError):
            BorderConfig(color="rebeccapurple")

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BorderConfig(top=-1)

    def test_above_max_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BorderConfig(bottom=9999)

    @pytest.mark.parametrize(
        ("factor", "expected"),
        [
            (0.5, (25, 100, 25, 25)),
            (1.0, (50, 200, 50, 50)),
            (0.1, (5, 20, 5, 5)),
        ],
    )
    def test_scaled(self, factor: float, expected: tuple[int, int, int, int]) -> None:
        scaled = BorderConfig(color=BLACK).scaled(factor)
        assert (scaled.top, scaled.bottom, scaled.left, scaled.right) == expected
        assert scaled.color == BLACK

    def test_scaled_floors_at_zero(self) -> None:
        scaled = BorderConfig(top=1).scaled(0.001)
        assert scaled.top >= 0


class TestMetadataConfig:
    def test_defaults(self) -> None:
        cfg = MetadataConfig()
        assert cfg.enabled is True
        assert cfg.position is MetadataPosition.BOTTOM_CENTER
        assert cfg.font is FontFamily.MONTSERRAT
        assert cfg.show_aperture and cfg.show_shutter_speed and cfg.show_iso
        assert not cfg.show_focal_length and not cfg.show_camera_model

    def test_font_size_bounds(self) -> None:
        with pytest.raises(ValidationError):
            MetadataConfig(font_size=4)
        with pytest.raises(ValidationError):
            MetadataConfig(font_size=1000)


class TestFontFamily:
    @pytest.mark.parametrize(
        ("family", "display", "filename"),
        [
            (FontFamily.MONTSERRAT, "Montserrat", "Montserrat-Regular.ttf"),
            (FontFamily.INTER, "Inter", "Inter-Regular.ttf"),
            (FontFamily.LORA, "Lora", "Lora-Regular.ttf"),
        ],
    )
    def test_display_and_filename(self, family: FontFamily, display: str, filename: str) -> None:
        assert family.display_name == display
        assert family.filename == filename

    def test_assets_exist(self) -> None:
        for family in FontFamily:
            asset = files("frame_tool").joinpath(f"assets/fonts/{family.filename}")
            assert asset.is_file(), f"Missing bundled font: {family.filename}"


class TestExifData:
    @pytest.fixture
    def full(self) -> ExifData:
        return ExifData(
            aperture=2.8,
            shutter_speed="1/250",
            iso=400,
            focal_length=35.0,
            camera_model="Sony A7IV",
        )

    def test_format_default_fields(self, full: ExifData) -> None:
        text = full.format(MetadataConfig())
        assert text == "f/2.8  ·  1/250s  ·  ISO 400"

    def test_format_all_fields(self, full: ExifData) -> None:
        cfg = MetadataConfig(show_focal_length=True, show_camera_model=True)
        text = full.format(cfg)
        assert "f/2.8" in text
        assert "1/250s" in text
        assert "ISO 400" in text
        assert "35mm" in text
        assert "Sony A7IV" in text

    def test_format_skips_missing(self) -> None:
        partial = ExifData(aperture=4.0, iso=100)
        text = partial.format(MetadataConfig())
        assert text == "f/4  ·  ISO 100"

    def test_format_empty_when_disabled(self, full: ExifData) -> None:
        cfg = MetadataConfig(show_aperture=False, show_shutter_speed=False, show_iso=False)
        assert full.format(cfg) == ""

    def test_format_respects_separator(self, full: ExifData) -> None:
        cfg = MetadataConfig(separator=" | ")
        assert full.format(cfg) == "f/2.8 | 1/250s | ISO 400"


class TestFrameJob:
    def test_missing_input_dir(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="does not exist"):
            FrameJob(input_dir=tmp_path / "nope", output_dir=tmp_path / "out")

    def test_input_must_be_dir(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("x")
        with pytest.raises(ValidationError, match="not a directory"):
            FrameJob(input_dir=f, output_dir=tmp_path / "out")

    def test_valid_job(self, tmp_path: Path) -> None:
        job = FrameJob(input_dir=tmp_path, output_dir=tmp_path / "out")
        assert isinstance(job.border, BorderConfig)
        assert isinstance(job.metadata, MetadataConfig)
