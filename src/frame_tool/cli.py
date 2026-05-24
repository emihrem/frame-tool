import logging
from pathlib import Path
from typing import Annotated

import typer

from frame_tool import presets as preset_store
from frame_tool.batch import process_folder
from frame_tool.colors import WHITE, parse_color
from frame_tool.models import (
    BorderConfig,
    CaptionConfig,
    FontFamily,
    FrameJob,
    InstagramConfig,
    InstagramPreset,
    MetadataConfig,
    MetadataPosition,
    Preset,
    WatermarkConfig,
    WatermarkPosition,
)

app = typer.Typer(
    name="frame-tool",
    help="Add borders and EXIF metadata to JPG photos.",
    no_args_is_help=False,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        from frame_tool.gui.app import launch_gui

        raise typer.Exit(code=launch_gui())


@app.command(help="Launch the graphical interface.")
def gui() -> None:
    from frame_tool.gui.app import launch_gui

    raise typer.Exit(code=launch_gui())


@app.command(help="Process a folder of JPG images in batch.")
def process(
    input_dir: Annotated[Path, typer.Argument(help="Folder containing JPG images.")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output folder. Defaults to <input>/framed."),
    ] = None,
    top: Annotated[int, typer.Option(help="Top border in pixels.")] = 50,
    bottom: Annotated[int, typer.Option(help="Bottom border in pixels.")] = 200,
    left: Annotated[int, typer.Option(help="Left border in pixels.")] = 50,
    right: Annotated[int, typer.Option(help="Right border in pixels.")] = 50,
    color: Annotated[
        str,
        typer.Option(
            help="Border color: hex (#RRGGBB) or named (white, black, cream, gray, charcoal…).",
        ),
    ] = WHITE,
    metadata_position: Annotated[
        MetadataPosition,
        typer.Option("--metadata-position", help="Where to render EXIF metadata."),
    ] = MetadataPosition.BOTTOM_CENTER,
    font: Annotated[
        FontFamily, typer.Option(help="Font family for metadata text.")
    ] = FontFamily.MONTSERRAT,
    font_size: Annotated[int, typer.Option(help="Metadata font size in pixels.")] = 36,
    no_metadata: Annotated[
        bool, typer.Option("--no-metadata", help="Disable metadata overlay.")
    ] = False,
    no_aperture: Annotated[bool, typer.Option("--no-aperture", help="Hide aperture.")] = False,
    no_shutter: Annotated[bool, typer.Option("--no-shutter", help="Hide shutter speed.")] = False,
    no_iso: Annotated[bool, typer.Option("--no-iso", help="Hide ISO.")] = False,
    focal_length: Annotated[
        bool, typer.Option("--focal-length", help="Include focal length.")
    ] = False,
    camera_model: Annotated[
        bool, typer.Option("--camera-model", help="Include camera model.")
    ] = False,
    instagram: Annotated[
        InstagramPreset,
        typer.Option(
            "--instagram",
            help=(
                "Pad output to an Instagram-friendly aspect ratio. "
                "'auto' picks based on each image's orientation."
            ),
        ),
    ] = InstagramPreset.NONE,
    instagram_size: Annotated[
        int | None,
        typer.Option(
            "--instagram-size",
            help="Downscale long edge to this many pixels (e.g. 1080 for Instagram).",
        ),
    ] = None,
    caption: Annotated[
        str,
        typer.Option(
            "--caption", help="Free-text caption rendered in the border (e.g. '© 2026 Emi')."
        ),
    ] = "",
    caption_position: Annotated[
        MetadataPosition,
        typer.Option("--caption-position", help="Where to render the caption text."),
    ] = MetadataPosition.BOTTOM_LEFT,
    caption_font: Annotated[
        FontFamily, typer.Option("--caption-font", help="Font family for the caption.")
    ] = FontFamily.MONTSERRAT,
    caption_font_size: Annotated[
        int, typer.Option("--caption-font-size", help="Caption font size in pixels.")
    ] = 28,
    watermark: Annotated[
        Path | None,
        typer.Option(
            "--watermark", help="PNG with transparency to overlay (logo / signature).", exists=True
        ),
    ] = None,
    watermark_position: Annotated[
        WatermarkPosition,
        typer.Option("--watermark-position", help="Where the watermark sits."),
    ] = WatermarkPosition.BOTTOM_RIGHT,
    watermark_opacity: Annotated[
        float, typer.Option("--watermark-opacity", help="0.0 (invisible) to 1.0 (opaque).")
    ] = 1.0,
    watermark_size: Annotated[
        float,
        typer.Option(
            "--watermark-size",
            help="Watermark width as fraction of the canvas long edge (e.g. 0.12).",
        ),
    ] = 0.1,
    preset: Annotated[
        str | None,
        typer.Option(
            "--preset",
            help="Load a saved preset by name. Overrides all other rendering flags.",
        ),
    ] = None,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if preset is not None:
        try:
            saved = preset_store.load_preset(preset)
        except KeyError as exc:
            raise typer.BadParameter(str(exc), param_hint="--preset") from exc
        job = FrameJob(
            input_dir=input_dir,
            output_dir=output or (input_dir / "framed"),
            border=saved.border,
            metadata=saved.metadata,
            instagram=saved.instagram,
            caption=saved.caption,
            watermark=saved.watermark,
        )
        _run_job(job)
        return

    try:
        parsed_color = parse_color(color)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--color") from exc

    job = FrameJob(
        input_dir=input_dir,
        output_dir=output or (input_dir / "framed"),
        border=BorderConfig(top=top, bottom=bottom, left=left, right=right, color=parsed_color),
        metadata=MetadataConfig(
            enabled=not no_metadata,
            position=metadata_position,
            font=font,
            font_size=font_size,
            show_aperture=not no_aperture,
            show_shutter_speed=not no_shutter,
            show_iso=not no_iso,
            show_focal_length=focal_length,
            show_camera_model=camera_model,
        ),
        instagram=InstagramConfig(preset=instagram, downscale_to=instagram_size),
        caption=CaptionConfig(
            text=caption,
            position=caption_position,
            font=caption_font,
            font_size=caption_font_size,
        ),
        watermark=WatermarkConfig(
            path=watermark,
            position=watermark_position,
            opacity=watermark_opacity,
            size_ratio=watermark_size,
        ),
    )

    _run_job(job)


def _run_job(job: FrameJob) -> None:
    def report(current: int, total: int, file: Path) -> None:
        typer.echo(f"[{current}/{total}] {file.name}")

    written = process_folder(job, on_progress=report)
    typer.echo(f"Done. Wrote {len(written)} file(s) to {job.output_dir}")


@app.command("list-presets", help="List saved presets.")
def list_presets_cmd() -> None:
    names = preset_store.list_presets()
    if not names:
        typer.echo("(no presets saved yet)")
        return
    for name in names:
        typer.echo(name)


@app.command(
    "save-preset",
    help="Save the current settings (passed as flags) as a named preset.",
    context_settings={"allow_extra_args": False},
)
def save_preset_cmd(
    name: Annotated[str, typer.Argument(help="Preset name.")],
    color: Annotated[str, typer.Option(help="Border color.")] = WHITE,
    top: Annotated[int, typer.Option()] = 50,
    bottom: Annotated[int, typer.Option()] = 200,
    left: Annotated[int, typer.Option()] = 50,
    right: Annotated[int, typer.Option()] = 50,
    metadata_position: Annotated[
        MetadataPosition, typer.Option("--metadata-position")
    ] = MetadataPosition.BOTTOM_CENTER,
    font: Annotated[FontFamily, typer.Option()] = FontFamily.MONTSERRAT,
    font_size: Annotated[int, typer.Option()] = 36,
    caption: Annotated[str, typer.Option()] = "",
    caption_position: Annotated[
        MetadataPosition, typer.Option("--caption-position")
    ] = MetadataPosition.BOTTOM_LEFT,
    instagram: Annotated[InstagramPreset, typer.Option()] = InstagramPreset.NONE,
    instagram_size: Annotated[int | None, typer.Option("--instagram-size")] = None,
    watermark: Annotated[Path | None, typer.Option(exists=True)] = None,
    watermark_position: Annotated[
        WatermarkPosition, typer.Option("--watermark-position")
    ] = WatermarkPosition.BOTTOM_RIGHT,
    watermark_opacity: Annotated[float, typer.Option("--watermark-opacity")] = 1.0,
    watermark_size: Annotated[float, typer.Option("--watermark-size")] = 0.1,
) -> None:
    try:
        parsed_color = parse_color(color)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--color") from exc

    try:
        preset = Preset(
            name=name,
            border=BorderConfig(top=top, bottom=bottom, left=left, right=right, color=parsed_color),
            metadata=MetadataConfig(position=metadata_position, font=font, font_size=font_size),
            instagram=InstagramConfig(preset=instagram, downscale_to=instagram_size),
            caption=CaptionConfig(text=caption, position=caption_position, font=font),
            watermark=WatermarkConfig(
                path=watermark,
                position=watermark_position,
                opacity=watermark_opacity,
                size_ratio=watermark_size,
            ),
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    preset_store.save_preset(preset)
    typer.echo(f"Saved preset '{name}' to {preset_store.PRESETS_PATH}")


@app.command("delete-preset", help="Delete a saved preset by name.")
def delete_preset_cmd(name: Annotated[str, typer.Argument(help="Preset name.")]) -> None:
    if name not in preset_store.list_presets():
        raise typer.BadParameter(f"Preset not found: {name}")
    preset_store.delete_preset(name)
    typer.echo(f"Deleted preset '{name}'")


if __name__ == "__main__":
    app()
