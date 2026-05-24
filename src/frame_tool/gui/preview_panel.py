from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class PreviewPanel(QWidget):
    navigate = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("previewPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(12)

        self._image_label = QLabel("Select a folder to begin")
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._image_label.setMinimumSize(400, 300)
        layout.addWidget(self._image_label, stretch=1)

        nav_row = QHBoxLayout()
        nav_row.setSpacing(12)
        nav_row.addStretch(1)

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setObjectName("nav")
        self._prev_btn.clicked.connect(lambda: self.navigate.emit(-1))
        nav_row.addWidget(self._prev_btn)

        self._counter = QLabel("—")
        self._counter.setObjectName("counter")
        self._counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._counter.setMinimumWidth(120)
        nav_row.addWidget(self._counter)

        self._next_btn = QPushButton("▶")
        self._next_btn.setObjectName("nav")
        self._next_btn.clicked.connect(lambda: self.navigate.emit(1))
        nav_row.addWidget(self._next_btn)
        nav_row.addStretch(1)
        layout.addLayout(nav_row)

        self._pixmap: QPixmap | None = None
        self.set_navigation_enabled(False)

    def set_image(self, pil_image: Image.Image, filename: str) -> None:
        qt_image = ImageQt(pil_image.convert("RGBA"))
        self._pixmap = QPixmap.fromImage(qt_image)
        self._image_label.setText("")
        self._rescale()
        self._image_label.setToolTip(filename)

    def clear(self) -> None:
        self._pixmap = None
        self._image_label.clear()
        self._image_label.setText("Select a folder to begin")

    def update_counter(self, index: int, total: int, filename: str) -> None:
        if total == 0:
            self._counter.setText("—")
            return
        self._counter.setText(f"{index + 1} / {total}   ·   {filename}")

    def set_navigation_enabled(self, enabled: bool) -> None:
        self._prev_btn.setEnabled(enabled)
        self._next_btn.setEnabled(enabled)

    def _rescale(self) -> None:
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self._image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._rescale()


def folder_to_filename(path: Path) -> str:
    return path.name
