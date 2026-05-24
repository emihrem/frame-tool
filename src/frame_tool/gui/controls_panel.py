from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from frame_tool.models import (
    BorderColor,
    BorderConfig,
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

        container = QWidget()
        container.setObjectName("sidePanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(self._build_border_group())
        layout.addWidget(self._build_metadata_group())
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
        color_row.setSpacing(16)
        color_row.addWidget(QLabel("Color"))
        self._white = QRadioButton("White")
        self._black = QRadioButton("Black")
        self._white.setChecked(self._border.color is BorderColor.WHITE)
        self._black.setChecked(self._border.color is BorderColor.BLACK)
        group_btn = QButtonGroup(group)
        group_btn.addButton(self._white)
        group_btn.addButton(self._black)
        self._white.toggled.connect(self._sync)
        color_row.addWidget(self._white)
        color_row.addWidget(self._black)
        color_row.addStretch(1)
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
        self._position.setCurrentIndex(
            list(_POSITION_LABELS.keys()).index(self._metadata.position)
        )
        self._position.currentIndexChanged.connect(self._sync)
        position_row.addWidget(self._position, stretch=1)
        layout.addLayout(position_row)

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

    def _sync(self) -> None:
        self._border = BorderConfig(
            top=self._top.value(),
            bottom=self._bottom.value(),
            left=self._left.value(),
            right=self._right.value(),
            color=BorderColor.WHITE if self._white.isChecked() else BorderColor.BLACK,
        )
        self._metadata = MetadataConfig(
            enabled=self._enabled.isChecked(),
            position=self._position.currentData(),
            font_size=self._font_size.value(),
            margin=self._metadata.margin,
            show_aperture=self._aperture.isChecked(),
            show_shutter_speed=self._shutter.isChecked(),
            show_iso=self._iso.isChecked(),
            show_focal_length=self._focal.isChecked(),
            show_camera_model=self._camera.isChecked(),
        )
        self.configChanged.emit()

    @property
    def border(self) -> BorderConfig:
        return self._border

    @property
    def metadata(self) -> MetadataConfig:
        return self._metadata
