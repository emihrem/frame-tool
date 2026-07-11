# Changelog

All notable changes to this project are documented here.

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] — 2026-07-10

### Fixed

- **GUI crash while navigating photos.** Background preview/export/update workers were destroyed on the wrong thread — their `deleteLater()` was tied to `thread.finished`, by which point the worker's event loop had stopped, so Python later freed the C++ object on the main thread and corrupted Qt's per-thread state (`shared QObject was deleted directly` → access violation). Workers are now deleted on their own thread while its loop is still alive.

### Engineering

- Added `PySide6` and `typer` to the mypy pre-commit hook so it type-checks against real Qt/Typer signatures.

## [0.3.0] — 2026-05-24

### Added

- **Free-form border colour**: pick any hex (`#RRGGBB`) via `QColorDialog` in the GUI, or pass `--color "#F5F5DC"` / `--color cream` in the CLI. Text colour auto-flips for contrast.
- **Free-text caption** rendered in the border alongside the EXIF line. Independent position, font, and size so EXIF and caption can sit in different corners.
- **PNG watermark / signature overlay** with configurable position, opacity, and size (as a fraction of the canvas's long edge). Composited via alpha-blending; transparency preserved.
- **Saveable presets**: bundle every render setting under a name (`~/.frame_tool/presets.json`). New CLI subcommands `save-preset`, `list-presets`, `delete-preset`, plus a `--preset NAME` flag on `process`. GUI top-bar combo + Save / Delete buttons.

### Changed

- Border colour storage went from a `white`/`black` enum to a hex string. CLI back-compat preserved through named-colour parsing.
- 137 → 160 tests; coverage still ~82%.

## [0.2.0] — 2026-05-24

First public release.

### Added

- **Core framing**: per-side white/black borders (`--top / --bottom / --left / --right`) applied to JPGs while preserving original JPEG quality and EXIF (`quality="keep"`, `subsampling="keep"`).
- **EXIF overlay**: aperture, shutter speed, ISO, focal length, and camera model rendered onto the border in six positions (`bottom-center`, `bottom-left`, `bottom-right`, `top-*`).
- **Three bundled typefaces** under SIL OFL 1.1 — Montserrat (default), Inter, Lora — so output looks the same on every OS.
- **Instagram-friendly export**: pad framed images to 1:1, 4:5, 1.91:1 or 9:16 (or `auto` per image orientation) so Instagram doesn't crop the composition. Optional `--instagram-size 1080` downscales the long edge to the exact IG canvas; without it, full resolution is preserved.
- **GUI** built with PySide6: dark theme, three-pane layout, live preview that updates as you tweak controls, font dropdown with each typeface previewed in its own style.
- **CLI** with Typer: `frame-tool process <folder>` for batch jobs, `frame-tool` (no args) launches the GUI.
- **PyInstaller bundling**: `pyinstaller packaging/frame_tool.spec` produces a standalone `frame_tool.app` on macOS and an executable folder on Windows / Linux — end users don't need Python.

### Engineering

- 97 tests (unit + integration + GUI smoke) at ~82% coverage.
- Ruff for lint + format, Mypy for type checking, both clean.
- GitHub Actions CI matrix: Linux / macOS / Windows × Python 3.11 / 3.12.
- Codecov uploads, pre-commit hooks for ruff and mypy.

[0.3.1]: https://github.com/emihrem/frame-tool/releases/tag/v0.3.1
[0.3.0]: https://github.com/emihrem/frame-tool/releases/tag/v0.3.0
[0.2.0]: https://github.com/emihrem/frame-tool/releases/tag/v0.2.0
