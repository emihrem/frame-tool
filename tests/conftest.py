import os
from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image
from PIL.ExifTags import Base as ExifTag

# Disable the GUI's GitHub release check during tests so we don't hit the
# network or segfault on threads racing during teardown.
os.environ.setdefault("FRAME_TOOL_NO_UPDATE_CHECK", "1")


def _build_exif_bytes(
    aperture: float | None = 2.8,
    exposure: float | None = 1 / 250,
    iso: int | None = 400,
    focal: float | None = 35.0,
    model: str | None = "Test Camera",
) -> bytes:
    img = Image.new("RGB", (1, 1))
    exif = img.getexif()
    if aperture is not None:
        exif[ExifTag.FNumber.value] = aperture
    if exposure is not None:
        exif[ExifTag.ExposureTime.value] = exposure
    if iso is not None:
        exif[ExifTag.ISOSpeedRatings.value] = iso
    if focal is not None:
        exif[ExifTag.FocalLength.value] = focal
    if model is not None:
        exif[ExifTag.Model.value] = model
    return exif.tobytes()


JpgFactory = Callable[..., Path]


@pytest.fixture
def jpg_factory(tmp_path: Path) -> JpgFactory:
    """Build a JPG fixture with optional synthetic EXIF.

    Usage:
        path = jpg_factory("photo.jpg", size=(800, 600), aperture=4.0)
    """

    def _make(
        name: str = "photo.jpg",
        size: tuple[int, int] = (800, 600),
        color: tuple[int, int, int] = (40, 100, 180),
        with_exif: bool = True,
        **exif_overrides: object,
    ) -> Path:
        img = Image.new("RGB", size, color)
        path = tmp_path / name
        kwargs: dict[str, object] = {"format": "JPEG", "quality": 95}
        if with_exif:
            kwargs["exif"] = _build_exif_bytes(**exif_overrides)  # type: ignore[arg-type]
        img.save(path, **kwargs)
        return path

    return _make


@pytest.fixture
def jpg_folder(jpg_factory: JpgFactory, tmp_path: Path) -> Path:
    """A folder containing three JPGs with EXIF."""
    for i in range(3):
        jpg_factory(name=f"img_{i}.jpg", size=(640, 480))
    return tmp_path
