from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from frame_tool.colors import WHITE, parse_color


class InstagramPreset(StrEnum):
    """Aspect ratios accepted by Instagram in 2026.

    ``AUTO`` picks the closest preset based on the original orientation:
    landscape → landscape 1.91:1, portrait → portrait 4:5, square → 1:1.
    """

    NONE = "none"
    SQUARE = "square"
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    STORY = "story"
    AUTO = "auto"

    @property
    def ratio(self) -> float | None:
        """Target width / height, or None for NONE / AUTO."""
        return {
            InstagramPreset.SQUARE: 1.0,
            InstagramPreset.PORTRAIT: 4 / 5,
            InstagramPreset.LANDSCAPE: 1.91,
            InstagramPreset.STORY: 9 / 16,
        }.get(self)

    def resolve(self, image_size: tuple[int, int]) -> "InstagramPreset":
        """Translate AUTO into a concrete preset for the given image."""
        if self is not InstagramPreset.AUTO:
            return self
        width, height = image_size
        if width > height:
            return InstagramPreset.LANDSCAPE
        if height > width:
            return InstagramPreset.PORTRAIT
        return InstagramPreset.SQUARE


class InstagramConfig(BaseModel):
    """Optional second pass that pads the framed image to an Instagram ratio.

    The user-defined border is applied first; this only adds *extra* padding on
    the two sides needed to reach ``preset.ratio``, in the same colour as the
    border. The image itself is never cropped or scaled in pixels — original
    resolution is preserved, and Instagram does its own downscale at upload.

    ``downscale_to`` (when set) resizes the long edge to that many pixels after
    padding. Use ``1080`` for the exact Instagram canvas; leave ``None`` to
    keep the source resolution.
    """

    preset: InstagramPreset = InstagramPreset.NONE
    downscale_to: int | None = Field(default=None, ge=320, le=8000)


class MetadataPosition(StrEnum):
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    TOP_CENTER = "top-center"
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"


class FontFamily(StrEnum):
    """Bundled font families used for the EXIF overlay."""

    MONTSERRAT = "montserrat"
    INTER = "inter"
    LORA = "lora"

    @property
    def display_name(self) -> str:
        return {
            FontFamily.MONTSERRAT: "Montserrat",
            FontFamily.INTER: "Inter",
            FontFamily.LORA: "Lora",
        }[self]

    @property
    def filename(self) -> str:
        return {
            FontFamily.MONTSERRAT: "Montserrat-Regular.ttf",
            FontFamily.INTER: "Inter-Regular.ttf",
            FontFamily.LORA: "Lora-Regular.ttf",
        }[self]


class BorderConfig(BaseModel):
    top: int = Field(default=50, ge=0, le=2000)
    bottom: int = Field(default=200, ge=0, le=2000)
    left: int = Field(default=50, ge=0, le=2000)
    right: int = Field(default=50, ge=0, le=2000)
    color: str = Field(default=WHITE)

    @field_validator("color", mode="before")
    @classmethod
    def _normalize_color(cls, value: str) -> str:
        return parse_color(value)

    def scaled(self, factor: float) -> "BorderConfig":
        return BorderConfig(
            top=max(0, round(self.top * factor)),
            bottom=max(0, round(self.bottom * factor)),
            left=max(0, round(self.left * factor)),
            right=max(0, round(self.right * factor)),
            color=self.color,
        )


class MetadataConfig(BaseModel):
    enabled: bool = True
    position: MetadataPosition = MetadataPosition.BOTTOM_CENTER
    font: FontFamily = FontFamily.MONTSERRAT
    font_size: int = Field(default=36, ge=8, le=400)
    margin: int = Field(default=24, ge=0, le=500)
    show_aperture: bool = True
    show_shutter_speed: bool = True
    show_iso: bool = True
    show_focal_length: bool = False
    show_camera_model: bool = False
    separator: str = "  ·  "


class ExifData(BaseModel):
    aperture: float | None = None
    shutter_speed: str | None = None
    iso: int | None = None
    focal_length: float | None = None
    camera_model: str | None = None

    def format(self, cfg: MetadataConfig) -> str:
        parts: list[str] = []
        if cfg.show_aperture and self.aperture is not None:
            parts.append(f"f/{self.aperture:g}")
        if cfg.show_shutter_speed and self.shutter_speed:
            parts.append(f"{self.shutter_speed}s")
        if cfg.show_iso and self.iso is not None:
            parts.append(f"ISO {self.iso}")
        if cfg.show_focal_length and self.focal_length is not None:
            parts.append(f"{self.focal_length:g}mm")
        if cfg.show_camera_model and self.camera_model:
            parts.append(self.camera_model)
        return cfg.separator.join(parts)


class WatermarkPosition(StrEnum):
    BOTTOM_RIGHT = "bottom-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    TOP_RIGHT = "top-right"
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"


class WatermarkConfig(BaseModel):
    """Optional logo / signature PNG composited inside the framed canvas.

    ``path is None`` disables rendering, so this can live on every job/preset
    without a separate enabled flag. ``size_ratio`` is the watermark width
    as a fraction of the canvas's longer side.
    """

    path: Path | None = None
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    size_ratio: float = Field(default=0.1, ge=0.01, le=1.0)
    margin: int = Field(default=40, ge=0, le=500)

    @field_validator("path")
    @classmethod
    def _path_must_exist(cls, value: Path | None) -> Path | None:
        if value is not None and not value.is_file():
            raise ValueError(f"Watermark file not found: {value}")
        return value


class CaptionConfig(BaseModel):
    """Free-text caption rendered in the border, separate from EXIF.

    An empty ``text`` disables rendering, so this can be added to every
    job/preset without a separate enabled flag.
    """

    text: str = ""
    position: MetadataPosition = MetadataPosition.BOTTOM_LEFT
    font: FontFamily = FontFamily.MONTSERRAT
    font_size: int = Field(default=28, ge=8, le=400)
    margin: int = Field(default=24, ge=0, le=500)


class Preset(BaseModel):
    """A named, reusable bundle of every render setting except input/output paths."""

    name: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9 _\-\.()]+$")
    border: BorderConfig = Field(default_factory=BorderConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    instagram: InstagramConfig = Field(default_factory=InstagramConfig)
    caption: CaptionConfig = Field(default_factory=CaptionConfig)
    watermark: WatermarkConfig = Field(default_factory=WatermarkConfig)


class FrameJob(BaseModel):
    input_dir: Path
    output_dir: Path
    border: BorderConfig = Field(default_factory=BorderConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    instagram: InstagramConfig = Field(default_factory=InstagramConfig)
    caption: CaptionConfig = Field(default_factory=CaptionConfig)
    watermark: WatermarkConfig = Field(default_factory=WatermarkConfig)

    @field_validator("input_dir")
    @classmethod
    def _input_must_exist(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"Input directory does not exist: {value}")
        if not value.is_dir():
            raise ValueError(f"Input path is not a directory: {value}")
        return value
