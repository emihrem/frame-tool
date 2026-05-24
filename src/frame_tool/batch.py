import logging
from collections.abc import Callable
from pathlib import Path

from frame_tool.exif import read_exif
from frame_tool.framer import apply_frame
from frame_tool.models import FrameJob

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".JPG", ".JPEG"})

ProgressCallback = Callable[[int, int, Path], None]


def find_images(input_dir: Path) -> list[Path]:
    seen: set[Path] = set()
    images: list[Path] = []
    for entry in sorted(input_dir.iterdir()):
        if entry.is_file() and entry.suffix in SUPPORTED_EXTENSIONS:
            resolved = entry.resolve()
            if resolved not in seen:
                seen.add(resolved)
                images.append(entry)
    return images


def _output_path(image: Path, output_dir: Path) -> Path:
    return output_dir / f"{image.stem}_framed{image.suffix.lower()}"


def process_folder(
    job: FrameJob,
    on_progress: ProgressCallback | None = None,
) -> list[Path]:
    images = find_images(job.input_dir)
    total = len(images)
    written: list[Path] = []

    for index, image in enumerate(images, start=1):
        if on_progress is not None:
            on_progress(index, total, image)
        try:
            exif = read_exif(image)
            output = _output_path(image, job.output_dir)
            apply_frame(
                image,
                output,
                job.border,
                job.metadata,
                exif,
                job.instagram,
                job.caption,
                job.watermark,
            )
            written.append(output)
        except (OSError, ValueError) as exc:
            logger.warning("Failed to process %s: %s", image, exc)
    return written
