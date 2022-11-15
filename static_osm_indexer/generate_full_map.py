import logging
from pathlib import Path
import tempfile
import importlib.resources as pkg_resources

import click

from static_osm_indexer.helpers import BoundingBox
from static_osm_indexer import generate_mbtiles
from static_osm_indexer import list_named_locations
from static_osm_indexer import index_locations_names
import static_osm_indexer.static_assets

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@click.command()
@click.argument(
    "input_pbf", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.argument(
    "bounding_box",
    type=click.STRING,
    callback=generate_mbtiles.validate_bounding_box,
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
    logger.info("Generating vector tiles...")
    generate_mbtiles.complete_mbtiles_generation(input_pbf, bounding_box, output_folder)
    logger.info("Extracting names to be indexed...")
    with tempfile.TemporaryDirectory() as tmpdirname:
        locations_list_fname = f"{tmpdirname}/all_names.jsonl"
        list_named_locations.dump_location_names(
            str(input_pbf), locations_list_fname, ["name"]
        )
        index_folder = output_folder / "locations_index"
        index_folder.mkdir()
        logger.info("Indexing location names...")

        index_locations_names.index_location_names(
            locations_list_fname, index_folder, 3, set()
        )
    logger.info("Copying static files...")

    ts_bundle_js = pkg_resources.read_text(
        static_osm_indexer.static_assets, "text_search.bundle.js"
    )
    with open(output_folder.absolute() / "text_search.bundle.js", "w") as fw:
        fw.write(ts_bundle_js)

    logger.info(f"Done! Static map stored at {output_folder.absolute()}")
