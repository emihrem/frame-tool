from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from frame_tool import presets as preset_store
from frame_tool.cli import app

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def isolated_preset_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep CLI preset commands out of the real ~/.frame_tool/."""
    fake_dir = tmp_path / "presets"
    monkeypatch.setattr(preset_store, "PRESETS_DIR", fake_dir)
    monkeypatch.setattr(preset_store, "PRESETS_PATH", fake_dir / "presets.json")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestProcessCommand:
    def test_basic_run(self, runner: CliRunner, jpg_folder: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        result = runner.invoke(
            app,
            ["process", str(jpg_folder), "-o", str(out), "--no-metadata"],
        )

        assert result.exit_code == 0, result.output
        assert "Wrote 3 file(s)" in result.output
        assert out.exists()
        assert len(list(out.glob("*.jpg"))) == 3

    def test_custom_borders(self, runner: CliRunner, jpg_folder: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        result = runner.invoke(
            app,
            [
                "process",
                str(jpg_folder),
                "-o",
                str(out),
                "--top",
                "10",
                "--bottom",
                "10",
                "--left",
                "10",
                "--right",
                "10",
                "--color",
                "black",
                "--no-metadata",
            ],
        )

        assert result.exit_code == 0, result.output

        with Image.open(next(out.glob("*.jpg"))) as img:
            assert img.size == (640 + 20, 480 + 20)
            r, g, b = img.convert("RGB").getpixel((5, 5))
            assert r < 20 and g < 20 and b < 20  # ~black, allowing JPEG chroma drift

    def test_missing_input_fails(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(app, ["process", str(tmp_path / "nope")])
        assert result.exit_code != 0

    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["process", "--help"])
        assert result.exit_code == 0
        assert "Process a folder" in result.output

    def test_default_output_in_subfolder(self, runner: CliRunner, jpg_folder: Path) -> None:
        result = runner.invoke(
            app,
            ["process", str(jpg_folder), "--no-metadata"],
        )
        assert result.exit_code == 0, result.output
        framed = jpg_folder / "framed"
        assert framed.exists()
        assert len(list(framed.glob("*.jpg"))) == 3

    @pytest.mark.parametrize(
        "extra",
        [
            ["--color", "white"],
            ["--color", "black"],
            ["--metadata-position", "top-left"],
            ["--metadata-position", "bottom-right"],
            ["--font-size", "20"],
            ["--focal-length", "--camera-model"],
            ["--no-aperture", "--no-shutter", "--no-iso"],
        ],
    )
    def test_flag_variants(
        self,
        runner: CliRunner,
        jpg_folder: Path,
        tmp_path: Path,
        extra: list[str],
    ) -> None:
        out = tmp_path / "out"
        result = runner.invoke(app, ["process", str(jpg_folder), "-o", str(out), *extra])
        assert result.exit_code == 0, result.output


class TestTopLevel:
    def test_help_lists_commands(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "process" in result.output
        assert "gui" in result.output
        assert "save-preset" in result.output
        assert "list-presets" in result.output


class TestPresetCommands:
    def test_list_when_empty(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["list-presets"])
        assert result.exit_code == 0
        assert "no presets" in result.output

    def test_save_list_delete_roundtrip(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app,
            [
                "save-preset",
                "wedding",
                "--color",
                "cream",
                "--top",
                "60",
                "--caption",
                "© Emi",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "wedding" in result.output

        listing = runner.invoke(app, ["list-presets"])
        assert "wedding" in listing.output

        delete = runner.invoke(app, ["delete-preset", "wedding"])
        assert delete.exit_code == 0

        listing2 = runner.invoke(app, ["list-presets"])
        assert "wedding" not in listing2.output

    def test_process_with_preset(self, runner: CliRunner, jpg_folder: Path, tmp_path: Path) -> None:
        runner.invoke(
            app,
            ["save-preset", "borderless", "--top", "10", "--bottom", "10"],
        )
        out = tmp_path / "out"
        result = runner.invoke(
            app, ["process", str(jpg_folder), "-o", str(out), "--preset", "borderless"]
        )
        assert result.exit_code == 0, result.output

        with Image.open(next(out.glob("*.jpg"))) as img:
            # Original is 640x480, preset has top=10 bottom=10 plus default left=50/right=50
            assert img.size == (640 + 100, 480 + 20)

    def test_process_with_missing_preset_errors(self, runner: CliRunner, jpg_folder: Path) -> None:
        result = runner.invoke(app, ["process", str(jpg_folder), "--preset", "nope"])
        assert result.exit_code != 0
        assert "nope" in result.output
