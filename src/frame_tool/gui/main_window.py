import logging
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from frame_tool.batch import find_images, process_folder
from frame_tool.exif import read_exif
from frame_tool.framer import render_preview
from frame_tool.models import (
    BorderConfig,
    ExifData,
    FrameJob,
    MetadataConfig,
)
from frame_tool.gui.controls_panel import ControlsPanel
from frame_tool.gui.preview_panel import PreviewPanel

logger = logging.getLogger(__name__)

_PREVIEW_DEBOUNCE_MS = 80


class _PreviewWorker(QObject):
    finished = Signal(object, str)
    failed = Signal(str)

    def __init__(
        self,
        image_path: Path,
        border: BorderConfig,
        metadata: MetadataConfig,
        exif: ExifData,
        max_dim: int,
    ) -> None:
        super().__init__()
        self._image_path = image_path
        self._border = border
        self._metadata = metadata
        self._exif = exif
        self._max_dim = max_dim

    @Slot()
    def run(self) -> None:
        try:
            image = render_preview(
                self._image_path,
                self._border,
                self._metadata,
                self._exif,
                self._max_dim,
            )
            self.finished.emit(image, self._image_path.name)
        except (OSError, ValueError) as exc:
            self.failed.emit(str(exc))


class _ExportWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(int, str)
    failed = Signal(str)

    def __init__(self, job: FrameJob) -> None:
        super().__init__()
        self._job = job

    @Slot()
    def run(self) -> None:
        try:
            def cb(current: int, total: int, file: Path) -> None:
                self.progress.emit(current, total, file.name)

            written = process_folder(self._job, on_progress=cb)
            self.finished.emit(len(written), str(self._job.output_dir))
        except (OSError, ValueError) as exc:
            self.failed.emit(str(exc))


class _ExifPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("exifPanel")
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("EXIF DATA")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self._fields: dict[str, tuple[QLabel, QLabel]] = {}
        for key, label in [
            ("aperture", "Aperture"),
            ("shutter_speed", "Shutter speed"),
            ("iso", "ISO"),
            ("focal_length", "Focal length"),
            ("camera_model", "Camera"),
        ]:
            label_widget = QLabel(label)
            label_widget.setObjectName("exifLabel")
            value_widget = QLabel("—")
            value_widget.setObjectName("exifValue")
            value_widget.setWordWrap(True)
            layout.addWidget(label_widget)
            layout.addWidget(value_widget)
            self._fields[key] = (label_widget, value_widget)

        layout.addStretch(1)

    def update(self, exif: ExifData | None) -> None:  # type: ignore[override]
        if exif is None:
            for _, value in self._fields.values():
                value.setText("—")
            return

        def fmt(key: str) -> str:
            value = getattr(exif, key)
            if value is None:
                return "—"
            if key == "aperture":
                return f"f/{value:g}"
            if key == "shutter_speed":
                return f"{value}s"
            if key == "iso":
                return f"ISO {value}"
            if key == "focal_length":
                return f"{value:g}mm"
            return str(value)

        for key, (_, value_widget) in self._fields.items():
            value_widget.setText(fmt(key))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("frame_tool")
        self.resize(1280, 800)

        self._images: list[Path] = []
        self._current_index: int = -1
        self._current_exif: ExifData | None = None
        self._input_dir: Path | None = None
        self._preview_thread: QThread | None = None
        self._preview_worker: _PreviewWorker | None = None
        self._export_thread: QThread | None = None
        self._export_worker: _ExportWorker | None = None
        self._export_dialog: QProgressDialog | None = None
        self._preview_pending: bool = False

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_PREVIEW_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._refresh_preview)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        splitter = QSplitter()
        splitter.setHandleWidth(1)

        self._controls = ControlsPanel()
        self._controls.configChanged.connect(self._on_config_changed)
        splitter.addWidget(self._controls)

        self._preview = PreviewPanel()
        self._preview.navigate.connect(self._navigate)
        splitter.addWidget(self._preview)

        self._exif_panel = _ExifPanel()
        splitter.addWidget(self._exif_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([340, 700, 240])
        root.addWidget(splitter, stretch=1)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready")

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        bar.setFixedHeight(56)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(10)

        title = QLabel("frame_tool")
        layout.addWidget(title)
        layout.addStretch(1)

        self._folder_label = QLabel("No folder selected")
        self._folder_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self._folder_label)

        open_btn = QPushButton("Open folder")
        open_btn.clicked.connect(self._select_folder)
        layout.addWidget(open_btn)

        self._export_btn = QPushButton("Export all")
        self._export_btn.setObjectName("primary")
        self._export_btn.clicked.connect(self._export)
        self._export_btn.setEnabled(False)
        layout.addWidget(self._export_btn)
        return bar

    def _select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder with JPG images")
        if not folder:
            return
        path = Path(folder)
        images = find_images(path)
        if not images:
            QMessageBox.warning(self, "No images", f"No JPG images found in {path}")
            return
        self._input_dir = path
        self._images = images
        self._current_index = 0
        self._folder_label.setText(f"{path.name}  ({len(images)} images)")
        self._export_btn.setEnabled(True)
        self._preview.set_navigation_enabled(len(images) > 1)
        self._load_current()

    def _navigate(self, delta: int) -> None:
        if not self._images:
            return
        self._current_index = (self._current_index + delta) % len(self._images)
        self._load_current()

    def _load_current(self) -> None:
        if not (0 <= self._current_index < len(self._images)):
            return
        image_path = self._images[self._current_index]
        self._preview.update_counter(self._current_index, len(self._images), image_path.name)
        try:
            self._current_exif = read_exif(image_path)
        except (OSError, ValueError) as exc:
            logger.warning("Failed to read EXIF for %s: %s", image_path, exc)
            self._current_exif = ExifData()
        self._exif_panel.update(self._current_exif)
        self._refresh_preview()

    def _on_config_changed(self) -> None:
        self._debounce.start()

    def _refresh_preview(self) -> None:
        if not (0 <= self._current_index < len(self._images)):
            return
        if self._preview_thread is not None and self._preview_thread.isRunning():
            self._preview_pending = True
            return
        image_path = self._images[self._current_index]
        exif = self._current_exif or ExifData()

        thread = QThread(self)
        worker = _PreviewWorker(
            image_path,
            self._controls.border,
            self._controls.metadata,
            exif,
            max_dim=1400,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_preview_ready)
        worker.failed.connect(self._on_preview_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._clear_preview_thread)
        self._preview_thread = thread
        self._preview_worker = worker
        thread.start()

    @Slot(object, str)
    def _on_preview_ready(self, image: object, filename: str) -> None:
        from PIL.Image import Image as PILImage

        if isinstance(image, PILImage):
            self._preview.set_image(image, filename)

    @Slot(str)
    def _on_preview_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"Preview failed: {message}", 5000)

    def _clear_preview_thread(self) -> None:
        self._preview_thread = None
        self._preview_worker = None
        if self._preview_pending:
            self._preview_pending = False
            self._refresh_preview()

    def _export(self) -> None:
        if not self._input_dir or not self._images:
            return
        suggested = self._input_dir / "framed"
        out = QFileDialog.getExistingDirectory(
            self, "Choose output folder", str(self._input_dir)
        )
        output_dir = Path(out) if out else suggested
        try:
            job = FrameJob(
                input_dir=self._input_dir,
                output_dir=output_dir,
                border=self._controls.border,
                metadata=self._controls.metadata,
            )
        except ValueError as exc:
            QMessageBox.critical(self, "Invalid configuration", str(exc))
            return

        self._export_dialog = QProgressDialog("Exporting…", "Cancel", 0, len(self._images), self)
        self._export_dialog.setWindowTitle("frame_tool")
        self._export_dialog.setMinimumDuration(0)
        self._export_dialog.setAutoClose(True)
        self._export_dialog.setAutoReset(False)
        self._export_dialog.setCancelButton(None)

        thread = QThread(self)
        worker = _ExportWorker(job)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_export_progress)
        worker.finished.connect(self._on_export_finished)
        worker.failed.connect(self._on_export_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._clear_export_thread)
        self._export_thread = thread
        self._export_worker = worker
        self._export_btn.setEnabled(False)
        thread.start()

    @Slot(int, int, str)
    def _on_export_progress(self, current: int, total: int, filename: str) -> None:
        if self._export_dialog is None:
            return
        self._export_dialog.setMaximum(total)
        self._export_dialog.setValue(current)
        self._export_dialog.setLabelText(f"[{current}/{total}] {filename}")

    @Slot(int, str)
    def _on_export_finished(self, count: int, output_dir: str) -> None:
        if self._export_dialog is not None:
            self._export_dialog.close()
            self._export_dialog = None
        self.statusBar().showMessage(f"Exported {count} file(s) to {output_dir}", 8000)
        QMessageBox.information(
            self,
            "Export complete",
            f"Wrote {count} file(s) to:\n{output_dir}",
        )

    @Slot(str)
    def _on_export_failed(self, message: str) -> None:
        if self._export_dialog is not None:
            self._export_dialog.close()
            self._export_dialog = None
        QMessageBox.critical(self, "Export failed", message)

    def _clear_export_thread(self) -> None:
        self._export_thread = None
        self._export_worker = None
        self._export_btn.setEnabled(True)

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        for thread in (self._preview_thread, self._export_thread):
            if thread is not None and thread.isRunning():
                thread.quit()
                thread.wait(2000)
        super().closeEvent(event)
