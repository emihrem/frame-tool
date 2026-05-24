from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from frame_tool.cli import app

pytestmark = pytest.mark.integration


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
