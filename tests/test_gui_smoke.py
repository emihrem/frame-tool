"""Smoke tests for the GUI — verify imports and basic instantiation.

These tests use the Qt offscreen platform plugin so they can run headless
on CI without a display.
"""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from frame_tool.batch import find_images  # noqa: E402
from frame_tool.gui.app import _load_stylesheet  # noqa: E402
from frame_tool.gui.controls_panel import ControlsPanel  # noqa: E402
from frame_tool.gui.main_window import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]


def test_imports_succeed() -> None:
    # Sanity: the heavy GUI modules import without side effects.
    assert MainWindow is not None
    assert ControlsPanel is not None


def test_main_window_constructs(qapp: QApplication) -> None:
    _ = qapp
    window = MainWindow()
    assert window.windowTitle() == "frame_tool"
    assert window.size().width() > 0
    window.close()


def test_controls_panel_emits_on_change(qapp: QApplication) -> None:
    _ = qapp
    panel = ControlsPanel()
    emitted: list[None] = []
    panel.configChanged.connect(lambda: emitted.append(None))

    initial = panel.border.top
    panel._top._slider.setValue(initial + 10)

    assert len(emitted) >= 1
    assert panel.border.top == initial + 10


def test_stylesheet_loads() -> None:
    qss = _load_stylesheet()
    assert "QPushButton" in qss
    assert len(qss) > 1000


def test_load_folder_into_window(qapp: QApplication, jpg_folder: Path) -> None:
    _ = qapp
    window = MainWindow()
    window._input_dir = jpg_folder
    window._images = find_images(jpg_folder)
    window._current_index = 0
    window._load_current()

    assert len(window._images) == 3
    assert window._current_exif is not None
    window.close()
