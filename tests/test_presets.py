"""Tests for the JSON preset store and the Preset model."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from frame_tool import presets as preset_store
from frame_tool.colors import BLACK
from frame_tool.models import (
    BorderConfig,
    CaptionConfig,
    InstagramConfig,
    InstagramPreset,
    MetadataConfig,
    Preset,
    WatermarkConfig,
)


@pytest.fixture(autouse=True)
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect PRESETS_PATH to a tmp file so tests don't touch the real store."""
    fake_dir = tmp_path / ".frame_tool"
    monkeypatch.setattr(preset_store, "PRESETS_DIR", fake_dir)
    monkeypatch.setattr(preset_store, "PRESETS_PATH", fake_dir / "presets.json")
    return fake_dir / "presets.json"


class TestPresetModel:
    def test_defaults(self) -> None:
        preset = Preset(name="basic")
        assert preset.name == "basic"
        assert preset.border.color  # default white
        assert preset.caption.text == ""
        assert preset.watermark.path is None

    @pytest.mark.parametrize("bad", ["", "name/with/slash", "name?", "a" * 65])
    def test_bad_names_rejected(self, bad: str) -> None:
        with pytest.raises(ValidationError):
            Preset(name=bad)

    @pytest.mark.parametrize(
        "good", ["wedding", "IG Square White", "Trip 2026", "default_v2", "preset.1"]
    )
    def test_good_names_accepted(self, good: str) -> None:
        assert Preset(name=good).name == good


class TestPresetStore:
    def test_empty_when_no_file(self) -> None:
        assert preset_store.list_presets() == []

    def test_save_and_load_roundtrip(self) -> None:
        original = Preset(
            name="wedding",
            border=BorderConfig(top=60, bottom=240, left=60, right=60, color=BLACK),
            metadata=MetadataConfig(font_size=42),
            caption=CaptionConfig(text="© 2026 Emi Mer"),
            instagram=InstagramConfig(preset=InstagramPreset.PORTRAIT, downscale_to=1080),
            watermark=WatermarkConfig(),
        )

        preset_store.save_preset(original)
        loaded = preset_store.load_preset("wedding")

        assert loaded.name == original.name
        assert loaded.border.color == BLACK
        assert loaded.border.top == 60
        assert loaded.caption.text == "© 2026 Emi Mer"
        assert loaded.instagram.preset is InstagramPreset.PORTRAIT
        assert loaded.instagram.downscale_to == 1080

    def test_save_creates_dir(self, isolated_store: Path) -> None:
        assert not isolated_store.parent.exists()
        preset_store.save_preset(Preset(name="test"))
        assert isolated_store.parent.exists()
        assert isolated_store.exists()

    def test_upsert_overwrites(self) -> None:
        preset_store.save_preset(Preset(name="x", border=BorderConfig(top=10)))
        preset_store.save_preset(Preset(name="x", border=BorderConfig(top=99)))

        loaded = preset_store.load_preset("x")
        assert loaded.border.top == 99
        assert preset_store.list_presets() == ["x"]

    def test_list_sorted(self) -> None:
        for name in ["zebra", "alpha", "mango"]:
            preset_store.save_preset(Preset(name=name))

        assert preset_store.list_presets() == ["alpha", "mango", "zebra"]

    def test_load_missing_raises(self) -> None:
        with pytest.raises(KeyError, match="Preset not found"):
            preset_store.load_preset("nope")

    def test_delete(self) -> None:
        preset_store.save_preset(Preset(name="ephemeral"))
        assert "ephemeral" in preset_store.list_presets()

        preset_store.delete_preset("ephemeral")
        assert "ephemeral" not in preset_store.list_presets()

    def test_delete_missing_is_noop(self) -> None:
        preset_store.delete_preset("nope")  # should not raise

    def test_corrupt_file_treated_as_empty(self, isolated_store: Path) -> None:
        isolated_store.parent.mkdir(parents=True, exist_ok=True)
        isolated_store.write_text("{not json", encoding="utf-8")
        assert preset_store.list_presets() == []
