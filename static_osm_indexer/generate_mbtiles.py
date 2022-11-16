import json
import logging
import os
from pathlib import Path
import importlib.resources as pkg_resources
import subprocess
import tempfile
import textwrap

import click

import static_osm_indexer.static_assets
from static_osm_indexer.helpers import BoundingBox

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def run_shell_command(command: str) -> None:
    logger.debug(f"Running command:\n{command}")
    status = os.system(textwrap.dedent(command).replace("\n", ""))
    if status != 0:
        logger.error(f"Error running command {command}")
        raise OSError(f"Non - status code: {status}")


def docker_image_exists(image_name: str) -> bool:
    """Check whether a Docker image exists on this machine."""
    result = subprocess.run(
        f"docker images {image_name}" " --format '{{json .}}'",
        check=True,
        shell=True,
        capture_output=True,
    )
    descr = result.stdout.decode()
    return any([descr.split("\n")])


def generate_mbtiles(
    input_pbf: Path,
    output_folder: Path,
    bounding_box: BoundingBox,
    config_path: str,
) -> None:
    """Generate the MBTiles using Tilemaker. Builds it if necessary."""
    if not docker_image_exists("tilemaker"):
        logger.info("Docker image for tilemaker not found, building it...")
        with tempfile.TemporaryDirectory() as tmpdirname:
            run_shell_command(
                "git clone https://github.com/systemed/tilemaker.git"
                f" {tmpdirname}/tilemaker"
            )
            run_shell_command(f"docker build {tmpdirname}/tilemaker/. -t tilemaker")

    if not output_folder.exists():
        # create it, or Docker will create it as root!
        output_folder.mkdir()
    run_shell_command(
        f"""
    docker run --rm
        -v {input_pbf.parent.absolute()}:/opt/input
        -v {output_folder.absolute()}:/opt/output
        -v {config_path}:/opt/config
        --user "$(id -u):$(id -g)"
        tilemaker  --input /opt/input/{input_pbf.name} --output /opt/output
        --config /opt/config/tilemaker_config.json
        --skip-integrity
        --bbox {str(bounding_box)}
    """
    )


def generate_pbf_fonts(output_folder: Path) -> None:
    """Generate PBF format fonts.

    This will install the nodejs library on a temporary folder and run it.
    The library is this one: https://github.com/openmaptiles/fonts
    It contains a we fonts in TTF format, and are converted to PBF files
    representing the glyphs as SDF matrices for use by mapboxgl
    """
    if not Path("fonts").exists():
        run_shell_command("git clone https://github.com/openmaptiles/fonts.git")
    # the dependency is super old, needs to be updated or doesn't work anymore
    # yep, this is even more cursed than the rest
    # see https://github.com/openmaptiles/fonts/issues/19
    with open("fonts/package.json") as fr:
        package_json = json.load(fr)
    package_json["dependencies"]["fontnik"] = "0.8.0-dev.2"
    with open("fonts/package.json", "w") as fw:
        json.dump(package_json, fw)
    run_shell_command("cd fonts && npm i && node generate.js")
    run_shell_command(f"cp -rv fonts/_output {output_folder.absolute()}/fonts")


def prepare_static_files(output_folder: Path, bounding_box: BoundingBox) -> None:
    """Copy the static files necessary to use the tiles."""
    index_html = pkg_resources.read_text(static_osm_indexer.static_assets, "index.html")
    p1 = (bounding_box.minlon + bounding_box.maxlon) / 2
    p2 = (bounding_box.minlat + bounding_box.maxlat) / 2

    index_html = index_html.replace("9.207356, 45.5113243", f"{p1:.7}, {p2:.7}")

    with open(output_folder.absolute() / "index.html", "w") as fw:
        fw.write(index_html)

    with open(output_folder.absolute() / "osm_liberty.json", "w") as fw:
        osm_style = pkg_resources.read_text(
            static_osm_indexer.static_assets, "osm_liberty.json"
        )
        fw.write(osm_style)


def validate_bounding_box(
    ctx: click.Context, param: click.Parameter, value: str
) -> BoundingBox:
    if not isinstance(value, str):
        raise click.BadParameter(f"must be a string, it was {type(value)}")
    try:
        [minlon, minlat, maxlon, maxlat] = value.split(",")
        return BoundingBox(float(minlon), float(minlat), float(maxlon), float(maxlat))
    except ValueError:
        raise click.BadParameter(
            f"format was not minlon, minlat, maxlon, maxlat It was: {value}"
        )


def complete_mbtiles_generation(
    input_pbf: Path,
    bounding_box: BoundingBox,
    output_folder: Path,
) -> None:
    logger.info(
        f"Processing {input_pbf.absolute()} to write in {output_folder.absolute()}"
    )
    logger.info("Generating the MBTiles")

    with tempfile.TemporaryDirectory() as tmpfolder:
        tilemaker_config = pkg_resources.read_text(
            static_osm_indexer.static_assets, "tilemaker_config.json"
        )
        with open(f"{tmpfolder}/tilemaker_config.json", "w") as cfw:
            cfw.write(tilemaker_config)
        generate_mbtiles(input_pbf, output_folder, bounding_box, tmpfolder)
    generate_pbf_fonts(output_folder)
    prepare_static_files(output_folder, bounding_box)


@click.command()
@click.argument(
    "input_pbf", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.argument(
    "bounding_box",
    type=click.STRING,
    callback=validate_bounding_box,
)
@click.argument(
    "output_folder",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("build"),
)
def main(
    input_pbf: Path,
    bounding_box: BoundingBox,
    output_folder: Path,
) -> None:
    complete_mbtiles_generation(input_pbf, bounding_box, output_folder)


if __name__ == "__main__":
    main()
