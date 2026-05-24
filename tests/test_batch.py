from pathlib import Path

import pytest
from PIL import Image

from frame_tool.batch import find_images, process_folder
from frame_tool.models import BorderConfig, FrameJob, MetadataConfig
from tests.conftest import JpgFactory

pytestmark = pytest.mark.integration


class TestFindImages:
    def test_finds_jpg_and_jpeg(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        jpg_factory(name="a.jpg")
        jpg_factory(name="b.JPG")
        jpg_factory(name="c.jpeg")
        (tmp_path / "ignore.png").write_bytes(b"x")
        (tmp_path / "ignore.txt").write_text("x")

        images = find_images(tmp_path)

        names = sorted(p.name for p in images)
        assert names == ["a.jpg", "b.JPG", "c.jpeg"]

    def test_sorted_result(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        for name in ["z.jpg", "a.jpg", "m.jpg"]:
            jpg_factory(name=name)

        images = find_images(tmp_path)
        assert [p.name for p in images] == ["a.jpg", "m.jpg", "z.jpg"]

    def test_empty_folder(self, tmp_path: Path) -> None:
        assert find_images(tmp_path) == []


class TestProcessFolder:
    def test_processes_all_images(self, jpg_folder: Path) -> None:
        job = FrameJob(
            input_dir=jpg_folder,
            output_dir=jpg_folder / "framed",
            border=BorderConfig(top=20, bottom=20, left=20, right=20),
            metadata=MetadataConfig(enabled=False),
        )

        written = process_folder(job)

        assert len(written) == 3
        for path in written:
            assert path.exists()
            assert path.name.endswith("_framed.jpg")

    def test_progress_callback_invoked(self, jpg_folder: Path) -> None:
        calls: list[tuple[int, int, str]] = []
        job = FrameJob(
            input_dir=jpg_folder,
            output_dir=jpg_folder / "out",
            metadata=MetadataConfig(enabled=False),
        )

        process_folder(job, on_progress=lambda c, t, p: calls.append((c, t, p.name)))

        assert len(calls) == 3
        assert calls[0][:2] == (1, 3)
        assert calls[-1][:2] == (3, 3)

    def test_skips_bad_files(self, jpg_folder: Path) -> None:
        (jpg_folder / "broken.jpg").write_bytes(b"not a jpeg")
        job = FrameJob(
            input_dir=jpg_folder,
            output_dir=jpg_folder / "out",
            metadata=MetadataConfig(enabled=False),
        )

        written = process_folder(job)

        assert len(written) == 3  # the 3 good ones; broken is logged + skipped

    def test_empty_folder_returns_empty(self, tmp_path: Path) -> None:
        job = FrameJob(input_dir=tmp_path, output_dir=tmp_path / "out")
        assert process_folder(job) == []

    def test_output_has_correct_dimensions(self, jpg_factory: JpgFactory, tmp_path: Path) -> None:
        jpg_factory(name="x.jpg", size=(500, 400))
        job = FrameJob(
            input_dir=tmp_path,
            output_dir=tmp_path / "out",
            border=BorderConfig(top=10, bottom=10, left=10, right=10),
            metadata=MetadataConfig(enabled=False),
        )

        written = process_folder(job)

        with Image.open(written[0]) as out:
            assert out.size == (520, 420)
