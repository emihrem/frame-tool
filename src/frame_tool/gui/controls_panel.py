from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from frame_tool.colors import BLACK, WHITE, contrast_for, rgb_to_hex
from frame_tool.framer import _load_font
from frame_tool.models import (
    BorderConfig,
    FontFamily,
    InstagramConfig,
    InstagramPreset,
    MetadataConfig,
    MetadataPosition,
)

_POSITION_LABELS: dict[MetadataPosition, str] = {
    MetadataPosition.BOTTOM_CENTER: "Bottom · Center",
    MetadataPosition.BOTTOM_LEFT: "Bottom · Left",
    MetadataPosition.BOTTOM_RIGHT: "Bottom · Right",
    MetadataPosition.TOP_CENTER: "Top · Center",
    MetadataPosition.TOP_LEFT: "Top · Left",
    MetadataPosition.TOP_RIGHT: "Top · Right",
}

_INSTAGRAM_LABELS: dict[InstagramPreset, str] = {
    InstagramPreset.NONE: "Off",
    InstagramPreset.AUTO: "Auto (per orientation)",
    InstagramPreset.SQUARE: "Square · 1:1",
    InstagramPreset.PORTRAIT: "Portrait · 4:5",
    InstagramPreset.LANDSCAPE: "Landscape · 1.91:1",
    InstagramPreset.STORY: "Story / Reel · 9:16",
}


class _ColorPicker(QWidget):
    """Swatch + quick W/B buttons + custom picker. Emits ``colorChanged(hex)``."""

    colorChanged = Signal(str)

    def __init__(self, initial: str = WHITE) -> None:
        super().__init__()
        self._color: str = initial

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._swatch = QPushButton()
        self._swatch.setFixedSize(36, 28)
        self._swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._swatch.clicked.connect(self._open_dialog)
        layout.addWidget(self._swatch)

        for label, hex_value in (("W", WHITE), ("B", BLACK)):
            btn = QPushButton(label)
            btn.setFixedWidth(32)
            btn.setObjectName("nav")
            btn.clicked.connect(lambda _checked=False, h=hex_value: self._set(h))
            layout.addWidget(btn)

        self._hex_label = QLabel(self._color)
        self._hex_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._hex_label, stretch=1)

        self._refresh_swatch()

    def value(self) -> str:
        return self._color

    def set_value(self, hex_color: str) -> None:
        if hex_color != self._color:
            self._set(hex_color, emit=False)

    def _set(self, hex_color: str, *, emit: bool = True) -> None:
        self._color = hex_color
        self._hex_label.setText(hex_color)
        self._refresh_swatch()
        if emit:
            self.colorChanged.emit(hex_color)

    def _refresh_swatch(self) -> None:
        border = "#444" if self._color.lower() != "#000000" else "#666"
        text_rgb = contrast_for(self._color)
        self._swatch.setStyleSheet(
            f"background-color: {self._color}; "
            f"border: 1px solid {border}; "
            f"border-radius: 4px; "
            f"color: {rgb_to_hex(text_rgb)};"
        )

    def _open_dialog(self) -> None:
        current = QColor(self._color)
        chosen = QColorDialog.getColor(current, self, "Choose border color")
        if chosen.isValid():
            self._set(chosen.name().upper())


def _render_font_preview(family: FontFamily, *, size: int = 22) -> QPixmap:
    """Render the font's display name in the font itself, as a small QPixmap.

    Used as the QComboBox item icon so the user can compare typefaces visually.
    """
    width, height = 200, 32
    canvas = Image.new("RGBA", (width, height), (15, 15, 15, 0))
    draw = ImageDraw.Draw(canvas)
    font = _load_font(size, family)
    draw.text((6, height // 2), family.display_name, font=font, fill=(230, 230, 230), anchor="lm")
    return QPixmap.fromImage(ImageQt(canvas))


class _SliderField(QWidget):
    valueChanged = Signal(int)

    def __init__(self, label: str, minimum: int, maximum: int, value: int) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        name = QLabel(label)
        name.setFixedWidth(58)
        layout.addWidget(name)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(minimum, maximum)
        self._slider.setValue(value)
        layout.addWidget(self._slider, stretch=1)

        self._spin = QSpinBox()
        self._spin.setRange(minimum, maximum)
        self._spin.setValue(value)
        self._spin.setSuffix(" px")
        layout.addWidget(self._spin)

        self._slider.valueChanged.connect(self._on_slider)
        self._spin.valueChanged.connect(self._on_spin)

    def _on_slider(self, value: int) -> None:
        if self._spin.value() != value:
            self._spin.blockSignals(True)
            self._spin.setValue(value)
            self._spin.blockSignals(False)
        self.valueChanged.emit(value)

    def _on_spin(self, value: int) -> None:
        if self._slider.value() != value:
            self._slider.blockSignals(True)
            self._slider.setValue(value)
            self._slider.blockSignals(False)
        self.valueChanged.emit(value)

    def value(self) -> int:
        return self._spin.value()


class ControlsPanel(QScrollArea):
    configChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("sidePanel")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._border = BorderConfig()
        self._metadata = MetadataConfig()
        self._instagram = InstagramConfig()

        container = QWidget()
        container.setObjectName("sidePanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(self._build_border_group())
        layout.addWidget(self._build_metadata_group())
        layout.addWidget(self._build_instagram_group())
        layout.addStretch(1)

        self.setWidget(container)
        self.setMinimumWidth(320)
        self.setMaximumWidth(420)

    def _build_border_group(self) -> QGroupBox:
        group = QGroupBox("Border")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self._top = _SliderField("Top", 0, 1000, self._border.top)
        self._bottom = _SliderField("Bottom", 0, 1000, self._border.bottom)
        self._left = _SliderField("Left", 0, 1000, self._border.left)
        self._right = _SliderField("Right", 0, 1000, self._border.right)
        for field in (self._top, self._bottom, self._left, self._right):
            layout.addWidget(field)
            field.valueChanged.connect(self._sync)

        color_row = QHBoxLayout()
        color_row.setContentsMargins(0, 6, 0, 0)
        color_row.setSpacing(10)
        color_label = QLabel("Color")
        color_label.setFixedWidth(58)
        color_row.addWidget(color_label)
        self._color_picker = _ColorPicker(self._border.color)
        self._color_picker.colorChanged.connect(self._sync)
        color_row.addWidget(self._color_picker, stretch=1)
        layout.addLayout(color_row)

        return group

    def _build_metadata_group(self) -> QGroupBox:
        group = QGroupBox("Metadata")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self._enabled = QCheckBox("Show metadata overlay")
        self._enabled.setChecked(self._metadata.enabled)
        self._enabled.toggled.connect(self._sync)
        layout.addWidget(self._enabled)

        layout.addSpacing(4)

        position_row = QHBoxLayout()
        position_row.setSpacing(10)
        position_row.addWidget(QLabel("Position"))
        self._position = QComboBox()
        for pos, label in _POSITION_LABELS.items():
            self._position.addItem(label, pos)
        self._position.setCurrentIndex(list(_POSITION_LABELS.keys()).index(self._metadata.position))
        self._position.currentIndexChanged.connect(self._sync)
        position_row.addWidget(self._position, stretch=1)
        layout.addLayout(position_row)

        font_row = QHBoxLayout()
        font_row.setSpacing(10)
        font_row.addWidget(QLabel("Font"))
        self._font = QComboBox()
        self._font.setIconSize(QSize(180, 28))
        for family in FontFamily:
            self._font.addItem(QIcon(_render_font_preview(family)), family.display_name, family)
        self._font.setCurrentIndex(list(FontFamily).index(self._metadata.font))
        self._font.currentIndexChanged.connect(self._sync)
        font_row.addWidget(self._font, stretch=1)
        layout.addLayout(font_row)

        self._font_size = _SliderField("Size", 8, 200, self._metadata.font_size)
        self._font_size.valueChanged.connect(self._sync)
        layout.addWidget(self._font_size)

        layout.addSpacing(4)
        fields_label = QLabel("Fields")
        fields_label.setObjectName("sectionTitle")
        layout.addWidget(fields_label)

        self._aperture = QCheckBox("Aperture (f/)")
        self._shutter = QCheckBox("Shutter speed")
        self._iso = QCheckBox("ISO")
        self._focal = QCheckBox("Focal length")
        self._camera = QCheckBox("Camera model")
        self._aperture.setChecked(self._metadata.show_aperture)
        self._shutter.setChecked(self._metadata.show_shutter_speed)
        self._iso.setChecked(self._metadata.show_iso)
        self._focal.setChecked(self._metadata.show_focal_length)
        self._camera.setChecked(self._metadata.show_camera_model)
        for check in (self._aperture, self._shutter, self._iso, self._focal, self._camera):
            check.toggled.connect(self._sync)
            layout.addWidget(check)

        return group

    def _build_instagram_group(self) -> QGroupBox:
        group = QGroupBox("Instagram")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(10)
        preset_row.addWidget(QLabel("Ratio"))
        self._ig_preset = QComboBox()
        for preset, label in _INSTAGRAM_LABELS.items():
            self._ig_preset.addItem(label, preset)
        self._ig_preset.setCurrentIndex(
            list(_INSTAGRAM_LABELS.keys()).index(self._instagram.preset)
        )
        self._ig_preset.currentIndexChanged.connect(self._sync)
        preset_row.addWidget(self._ig_preset, stretch=1)
        layout.addLayout(preset_row)

        self._ig_downscale = QCheckBox("Resize long edge to 1080 px")
        self._ig_downscale.setChecked(self._instagram.downscale_to is not None)
        self._ig_downscale.toggled.connect(self._sync)
        layout.addWidget(self._ig_downscale)

        hint = QLabel(
            "Pads the framed image with extra border to reach the target "
            "aspect ratio so Instagram doesn't crop it."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(hint)

        return group

    def _sync(self) -> None:
        self._border = BorderConfig(
            top=self._top.value(),
            bottom=self._bottom.value(),
            left=self._left.value(),
            right=self._right.value(),
            color=self._color_picker.value(),
        )
        self._metadata = MetadataConfig(
            enabled=self._enabled.isChecked(),
            position=self._position.currentData(),
            font=self._font.currentData(),
            font_size=self._font_size.value(),
            margin=self._metadata.margin,
            show_aperture=self._aperture.isChecked(),
            show_shutter_speed=self._shutter.isChecked(),
            show_iso=self._iso.isChecked(),
            show_focal_length=self._focal.isChecked(),
            show_camera_model=self._camera.isChecked(),
        )
        self._instagram = InstagramConfig(
            preset=self._ig_preset.currentData(),
            downscale_to=1080 if self._ig_downscale.isChecked() else None,
        )
        self.configChanged.emit()

    @property
    def border(self) -> BorderConfig:
        return self._border

    @property
    def metadata(self) -> MetadataConfig:
        return self._metadata

    @property
    def instagram(self) -> InstagramConfig:
        return self._instagram
