from fractions import Fraction
from pathlib import Path
from typing import SupportsFloat, cast

from PIL import ExifTags, Image

from frame_tool.models import ExifData

_TAG_FNUMBER = next(k for k, v in ExifTags.TAGS.items() if v == "FNumber")
_TAG_EXPOSURE = next(k for k, v in ExifTags.TAGS.items() if v == "ExposureTime")
_TAG_ISO = next(k for k, v in ExifTags.TAGS.items() if v == "ISOSpeedRatings")
_TAG_FOCAL = next(k for k, v in ExifTags.TAGS.items() if v == "FocalLength")
_TAG_MODEL = next(k for k, v in ExifTags.TAGS.items() if v == "Model")


def _format_shutter(value: float) -> str:
    if value >= 1:
        return f"{value:g}"
    frac = Fraction(value).limit_denominator(8000)
    return f"{frac.numerator}/{frac.denominator}"


def read_exif(image_path: Path) -> ExifData:
    with Image.open(image_path) as img:
        raw = img.getexif()
        if not raw:
            return ExifData()
        merged: dict[int, object] = dict(raw)
        for ifd_tag in (ExifTags.IFD.Exif, ExifTags.IFD.GPSInfo):
            try:
                merged.update(raw.get_ifd(ifd_tag))
            except (KeyError, AttributeError):
                continue

    aperture = merged.get(_TAG_FNUMBER)
    exposure = merged.get(_TAG_EXPOSURE)
    iso_raw = merged.get(_TAG_ISO)
    focal = merged.get(_TAG_FOCAL)
    model = merged.get(_TAG_MODEL)

    iso: int | None = None
    if isinstance(iso_raw, (list, tuple)) and iso_raw:
        iso = int(iso_raw[0])
    elif isinstance(iso_raw, (int, float)):
        iso = int(iso_raw)

    return ExifData(
        aperture=float(cast(SupportsFloat, aperture)) if aperture is not None else None,
        shutter_speed=(
            _format_shutter(float(cast(SupportsFloat, exposure))) if exposure is not None else None
        ),
        iso=iso,
        focal_length=float(cast(SupportsFloat, focal)) if focal is not None else None,
        camera_model=str(model).strip() if model else None,
    )
