"""Disk storage for named ``Preset`` bundles.

Stored as a single JSON file at ``~/.frame_tool/presets.json`` of shape
``{name: serialized_preset}``. Missing file is treated as empty so the first
use is transparent.
"""

import json
import logging
from pathlib import Path

from frame_tool.models import Preset

logger = logging.getLogger(__name__)

PRESETS_DIR: Path = Path.home() / ".frame_tool"
PRESETS_PATH: Path = PRESETS_DIR / "presets.json"


def _read_raw() -> dict[str, dict[str, object]]:
    if not PRESETS_PATH.exists():
        return {}
    try:
        text = PRESETS_PATH.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read presets file: %s", exc)
        return {}
    if not isinstance(data, dict):
        logger.warning("Presets file is not an object; ignoring")
        return {}
    return data


def _write_raw(data: dict[str, dict[str, object]]) -> None:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def list_presets() -> list[str]:
    return sorted(_read_raw().keys())


def load_preset(name: str) -> Preset:
    raw = _read_raw()
    if name not in raw:
        raise KeyError(f"Preset not found: {name}")
    return Preset.model_validate(raw[name])


def save_preset(preset: Preset) -> None:
    raw = _read_raw()
    raw[preset.name] = preset.model_dump(mode="json")
    _write_raw(raw)


def delete_preset(name: str) -> None:
    raw = _read_raw()
    if name in raw:
        del raw[name]
        _write_raw(raw)
