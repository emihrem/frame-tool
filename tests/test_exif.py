from pathlib import Path

import pytest

from frame_tool.exif import _format_shutter, read_exif
from tests.conftest import JpgFactory


class TestFormatShutter:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (1 / 250, "1/250"),
            (1 / 60, "1/60"),
            (1 / 4000, "1/4000"),
            (1.0, "1"),
            (2.5, "2.5"),
            (0.5, "1/2"),
        ],
    )
    def test_format(self, value: float, expected: str) -> None:
        assert _format_shutter(value) == expected


class TestReadExif:
    def test_full_exif(self, jpg_factory: JpgFactory) -> None:
        path = jpg_factory(
            aperture=4.0,
            exposure=1 / 125,
            iso=200,
            focal=50.0,
            model="Nikon Z9",
        )
        exif = read_exif(path)
        assert exif.aperture == 4.0
        assert exif.shutter_speed == "1/125"
        assert exif.iso == 200
        assert exif.focal_length == 50.0
        assert exif.camera_model == "Nikon Z9"

    def test_partial_exif(self, jpg_factory: JpgFactory) -> None:
        path = jpg_factory(aperture=2.0, iso=800, exposure=None, focal=None, model=None)
        exif = read_exif(path)
        assert exif.aperture == 2.0
        assert exif.iso == 800
        assert exif.shutter_speed is None
        assert exif.focal_length is None
        assert exif.camera_model is None

    def test_no_exif(self, jpg_factory: JpgFactory) -> None:
        path = jpg_factory(with_exif=False)
        exif = read_exif(path)
        assert exif.aperture is None
        assert exif.iso is None
        assert exif.shutter_speed is None

    def test_unreadable_file_raises(self, tmp_path: Path) -> None:
        bogus = tmp_path / "not_an_image.jpg"
        bogus.write_bytes(b"not a real jpeg")
        with pytest.raises((OSError, ValueError)):
            read_exif(bogus)
