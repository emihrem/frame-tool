# PyInstaller spec for frame_tool GUI
# Build with:  pyinstaller packaging/frame_tool.spec --noconfirm
# Output:      dist/frame_tool.app (macOS), dist/frame_tool/ (Linux/Windows)

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

PROJECT_ROOT = Path(SPECPATH).parent
ENTRY_SCRIPT = str(PROJECT_ROOT / "scripts" / "frame_tool_gui.py")
ICON_PATH = PROJECT_ROOT / "packaging" / "icon.icns"

datas = collect_data_files("frame_tool", includes=["assets/**/*", "gui/*.qss"])

a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=["PIL.ImageQt"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PySide6.QtNetwork",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtPdf",
        "PySide6.QtCharts",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="frame_tool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="frame_tool",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="frame_tool.app",
        icon=str(ICON_PATH) if ICON_PATH.exists() else None,
        bundle_identifier="com.frametool.app",
        info_plist={
            "CFBundleName": "frame_tool",
            "CFBundleDisplayName": "frame_tool",
            "CFBundleShortVersionString": "0.3.0",
            "CFBundleVersion": "0.3.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "10.15.0",
        },
    )
