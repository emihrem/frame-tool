import logging
from pathlib import Path
from typing import Annotated

import typer

from frame_tool.batch import process_folder
from frame_tool.models import (
    BorderColor,
    BorderConfig,
    FrameJob,
    MetadataConfig,
    MetadataPosition,
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
    color: Annotated[BorderColor, typer.Option(help="Border color.")] = BorderColor.WHITE,
    metadata_position: Annotated[
        MetadataPosition,
        typer.Option("--metadata-position", help="Where to render EXIF metadata."),
    ] = MetadataPosition.BOTTOM_CENTER,
    font_size: Annotated[int, typer.Option(help="Metadata font size in pixels.")] = 36,
    no_metadata: Annotated[bool, typer.Option("--no-metadata", help="Disable metadata overlay.")] = False,
    no_aperture: Annotated[bool, typer.Option("--no-aperture", help="Hide aperture.")] = False,
    no_shutter: Annotated[bool, typer.Option("--no-shutter", help="Hide shutter speed.")] = False,
    no_iso: Annotated[bool, typer.Option("--no-iso", help="Hide ISO.")] = False,
    focal_length: Annotated[bool, typer.Option("--focal-length", help="Include focal length.")] = False,
    camera_model: Annotated[bool, typer.Option("--camera-model", help="Include camera model.")] = False,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    job = FrameJob(
        input_dir=input_dir,
        output_dir=output or (input_dir / "framed"),
        border=BorderConfig(top=top, bottom=bottom, left=left, right=right, color=color),
        metadata=MetadataConfig(
            enabled=not no_metadata,
            position=metadata_position,
            font_size=font_size,
            show_aperture=not no_aperture,
            show_shutter_speed=not no_shutter,
            show_iso=not no_iso,
            show_focal_length=focal_length,
            show_camera_model=camera_model,
        ),
    )

    def report(current: int, total: int, file: Path) -> None:
        typer.echo(f"[{current}/{total}] {file.name}")

    written = process_folder(job, on_progress=report)
    typer.echo(f"Done. Wrote {len(written)} file(s) to {job.output_dir}")


if __name__ == "__main__":
    app()
