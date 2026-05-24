import sys
from importlib.resources import files

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from frame_tool.gui.main_window import MainWindow

_FONT_RESOURCE = files("frame_tool").joinpath("assets/fonts/Inter-Regular.ttf")
_STYLE_RESOURCE = files("frame_tool").joinpath("gui/style.qss")


def _load_stylesheet() -> str:
    try:
        return _STYLE_RESOURCE.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _register_font() -> None:
    try:
        with _FONT_RESOURCE.open("rb") as fh:
            data = fh.read()
    except (FileNotFoundError, OSError):
        return
    QFontDatabase.addApplicationFontFromData(data)


def launch_gui() -> int:
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
    app.setApplicationName("frame_tool")
    app.setOrganizationName("frame_tool")
    _register_font()
    app.setStyleSheet(_load_stylesheet())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(launch_gui())
