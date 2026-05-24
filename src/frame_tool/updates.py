"""Best-effort check for a newer GitHub release.

The check runs on a background thread at GUI launch. Network failures are
swallowed silently — never block startup, never show errors. Users can
opt out with ``FRAME_TOOL_NO_UPDATE_CHECK=1``.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import NamedTuple

from frame_tool import __version__

logger = logging.getLogger(__name__)

LATEST_RELEASE_URL = "https://api.github.com/repos/emihrem/frame-tool/releases/latest"
OPT_OUT_ENV = "FRAME_TOOL_NO_UPDATE_CHECK"
_USER_AGENT = f"frame_tool/{__version__}"


class UpdateInfo(NamedTuple):
    version: str
    html_url: str
    name: str


def _parse_version(raw: str) -> tuple[int, ...]:
    cleaned = raw.lstrip("vV").strip()
    if not cleaned:
        raise ValueError("empty version string")
    parts = cleaned.split(".")
    return tuple(int(p) for p in parts)


def check_for_update(
    current_version: str = __version__,
    *,
    timeout: float = 4.0,
) -> UpdateInfo | None:
    """Return ``UpdateInfo`` if GitHub has a newer tag, otherwise ``None``.

    Never raises: every failure path (no network, bad JSON, non-semver tag)
    just returns ``None`` so the caller can stay simple.
    """
    if os.environ.get(OPT_OUT_ENV):
        return None

    try:
        request = urllib.request.Request(
            LATEST_RELEASE_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": _USER_AGENT,
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        logger.debug("Update check failed: %s", exc)
        return None

    tag = payload.get("tag_name")
    url = payload.get("html_url")
    name = payload.get("name", tag)
    if not isinstance(tag, str) or not isinstance(url, str):
        return None

    try:
        latest_version = _parse_version(tag)
        current_parsed = _parse_version(current_version)
    except ValueError:
        return None

    if latest_version <= current_parsed:
        return None
    return UpdateInfo(version=tag.lstrip("vV"), html_url=url, name=name or tag)
