from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class BorderColor(StrEnum):
    WHITE = "white"
    BLACK = "black"

    @property
    def rgb(self) -> tuple[int, int, int]:
        return (255, 255, 255) if self is BorderColor.WHITE else (0, 0, 0)

    @property
    def contrast_rgb(self) -> tuple[int, int, int]:
        return (0, 0, 0) if self is BorderColor.WHITE else (255, 255, 255)


class MetadataPosition(StrEnum):
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    TOP_CENTER = "top-center"
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"


class BorderConfig(BaseModel):
    top: int = Field(default=50, ge=0, le=2000)
    bottom: int = Field(default=200, ge=0, le=2000)
    left: int = Field(default=50, ge=0, le=2000)
    right: int = Field(default=50, ge=0, le=2000)
    color: BorderColor = BorderColor.WHITE

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


class FrameJob(BaseModel):
    input_dir: Path
    output_dir: Path
    border: BorderConfig = Field(default_factory=BorderConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)

    @field_validator("input_dir")
    @classmethod
    def _input_must_exist(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"Input directory does not exist: {value}")
        if not value.is_dir():
            raise ValueError(f"Input path is not a directory: {value}")
        return value
