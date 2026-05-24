# frame_tool

Add white or black borders to JPG photos and stamp them with EXIF metadata (aperture, shutter speed, ISO). Cross-platform (macOS / Linux / Windows) with a modern dark GUI and a CLI for batch processing.

Built for photographers who edit in Lightroom and want a simple post-export step to add borders + shooting info — without ever touching the underlying JPEG quality.

## Features

- Independent border per side (top, bottom, left, right), white or black.
- Optional EXIF overlay with configurable position, size, and fields (f-stop, shutter, ISO, focal length, camera).
- Live preview as you tweak settings.
- Batch export an entire folder with one click (or one CLI command).
- Original JPEG quality and EXIF metadata preserved on export (`quality="keep"`, `subsampling="keep"`).
- Inter font bundled — same look on every OS.

## Install (recommended: `uv`)

```bash
# Install once, isolated, with auto-managed Python:
uv tool install --from . frame-tool

# Or, from a git remote later:
# uv tool install git+https://github.com/<you>/frame-tool
```

Then run from any directory:

```bash
frame-tool          # launches GUI
frame-tool gui      # explicit GUI launch
frame-tool --help   # CLI help
```

### Development setup

```bash
cd frame_tool
uv venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
uv pip install -e .
frame-tool
```

### Alternative: pipx

```bash
pipx install .
```

## GUI usage

1. Click **Open folder** and select a folder of JPGs.
2. Adjust border thickness per side, color, metadata position, font size, and fields.
3. Use ◀ / ▶ to flip through images and preview each one with the same settings.
4. Click **Export all** and pick an output folder (defaults to `<input>/framed/`).

## CLI usage

```bash
frame-tool process ./photos \
  --top 50 --bottom 240 --left 50 --right 50 \
  --color white \
  --metadata-position bottom-center \
  --font-size 36 \
  --focal-length \
  --output ./photos/framed
```

Flags:

| Flag | Default | Description |
|---|---|---|
| `--top / --bottom / --left / --right` | `50 / 200 / 50 / 50` | Border in px |
| `--color` | `white` | `white` or `black` |
| `--metadata-position` | `bottom-center` | `bottom-center`, `bottom-left`, `bottom-right`, `top-center`, `top-left`, `top-right` |
| `--font-size` | `36` | Metadata font size in px |
| `--no-metadata` | off | Disable text overlay entirely |
| `--no-aperture / --no-shutter / --no-iso` | shown | Hide a field |
| `--focal-length / --camera-model` | hidden | Include a field |
| `--output / -o` | `<input>/framed` | Output folder |

Output filenames are `<original>_framed.jpg`.

## Tech stack

- **Pillow** for image processing, EXIF, and text rendering.
- **Pydantic v2** for typed configuration models.
- **PySide6 (Qt)** for the GUI.
- **Typer** for the CLI.
- **uv** + **hatchling** for packaging.

## License

MIT. Bundled font: [Inter](https://github.com/rsms/inter) by Rasmus Andersson, SIL Open Font License 1.1 (see `src/frame_tool/assets/fonts/Inter-LICENSE.txt`).
