import pytest

from frame_tool.colors import (
    BLACK,
    WHITE,
    contrast_for,
    hex_to_rgb,
    parse_color,
    rgb_to_hex,
)


class TestParseColor:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("white", WHITE),
            ("WHITE", WHITE),
            ("black", BLACK),
            ("cream", "#F5F5DC"),
            ("gray", "#808080"),
            ("grey", "#808080"),
            ("#ff0000", "#FF0000"),
            ("#FF8800", "#FF8800"),
            ("ff0000", "#FF0000"),  # missing # gets added
        ],
    )
    def test_valid(self, raw: str, expected: str) -> None:
        assert parse_color(raw) == expected

    @pytest.mark.parametrize("bad", ["", "rebeccapurple", "#FFF", "#GGGGGG", "12345"])
    def test_invalid(self, bad: str) -> None:
        with pytest.raises(ValueError, match=r"(Invalid color|must not be empty)"):
            parse_color(bad)


class TestHexRgb:
    @pytest.mark.parametrize(
        ("hex_value", "rgb"),
        [
            ("#FFFFFF", (255, 255, 255)),
            ("#000000", (0, 0, 0)),
            ("#FF8800", (255, 136, 0)),
            ("#808080", (128, 128, 128)),
        ],
    )
    def test_hex_to_rgb(self, hex_value: str, rgb: tuple[int, int, int]) -> None:
        assert hex_to_rgb(hex_value) == rgb

    @pytest.mark.parametrize(
        ("rgb", "hex_value"),
        [
            ((255, 255, 255), "#FFFFFF"),
            ((0, 0, 0), "#000000"),
            ((255, 136, 0), "#FF8800"),
        ],
    )
    def test_rgb_to_hex(self, rgb: tuple[int, int, int], hex_value: str) -> None:
        assert rgb_to_hex(rgb) == hex_value

    def test_hex_to_rgb_invalid(self) -> None:
        with pytest.raises(ValueError, match="Not a valid"):
            hex_to_rgb("not a hex")


class TestContrastFor:
    @pytest.mark.parametrize(
        ("bg", "expected"),
        [
            ("#FFFFFF", (0, 0, 0)),  # white bg → black text
            ("#F5F5DC", (0, 0, 0)),  # cream → black
            ("#000000", (255, 255, 255)),  # black → white
            ("#202020", (255, 255, 255)),  # dark gray → white
            ("#808080", (255, 255, 255)),  # mid-gray → white (luminance == 128, > strict)
        ],
    )
    def test_contrast(self, bg: str, expected: tuple[int, int, int]) -> None:
        assert contrast_for(bg) == expected
