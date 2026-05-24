"""Color helpers for border / text rendering.

Border colors are stored as ``#RRGGBB`` strings throughout the codebase.
This module provides the parsing, conversion, and contrast utilities.
"""

import re

WHITE = "#FFFFFF"
BLACK = "#000000"

# A small named-color table so CLI users can write `--color cream`.
# Add freely — values are validated against the hex regex at parse time.
_NAMED_COLORS: dict[str, str] = {
    "white": WHITE,
    "black": BLACK,
    "cream": "#F5F5DC",
    "ivory": "#FFFFF0",
    "gray": "#808080",
    "grey": "#808080",
    "charcoal": "#2F2F2F",
    "lightgray": "#D3D3D3",
    "lightgrey": "#D3D3D3",
    "darkgray": "#404040",
    "darkgrey": "#404040",
}

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def parse_color(value: str) -> str:
    """Accept a hex string (``#RRGGBB``) or a named color, return canonical ``#RRGGBB``."""
    if not value:
        raise ValueError("Color must not be empty.")
    normalized = value.strip()
    if normalized.lower() in _NAMED_COLORS:
        return _NAMED_COLORS[normalized.lower()]
    if not normalized.startswith("#"):
        normalized = "#" + normalized
    if not _HEX_RE.match(normalized):
        raise ValueError(
            f"Invalid color {value!r}. Use a named color "
            f"({', '.join(sorted(_NAMED_COLORS))}) or hex like #FF8800."
        )
    return normalized.upper()


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    if not _HEX_RE.match(hex_str):
        raise ValueError(f"Not a valid #RRGGBB color: {hex_str!r}")
    return (int(hex_str[1:3], 16), int(hex_str[3:5], 16), int(hex_str[5:7], 16))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


def contrast_for(hex_str: str) -> tuple[int, int, int]:
    """Black or white, whichever reads best on top of ``hex_str``.

    Uses the W3C perceived-luminance formula.
    """
    r, g, b = hex_to_rgb(hex_str)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return (0, 0, 0) if luminance > 128 else (255, 255, 255)
