import importlib.resources as pkg_resources
from pathlib import Path

import pytest

from static_osm_indexer import generate_mbtiles
import static_osm_indexer.static_assets
from static_osm_indexer.helpers import BoundingBox

@pytest.mark.skip("Running this each time is too much")
def test_generate_mbtiles(tmp_path, pbf_input_sample):
    tilemaker_config = pkg_resources.read_text(
        static_osm_indexer.static_assets, "tilemaker_config.json"
    )
    with open(f"{tmp_path}/tilemaker_config.json", "w") as cfw:
        cfw.write(tilemaker_config)
    generate_mbtiles.generate_mbtiles(
        pbf_input_sample,
        Path(tmp_path),
        BoundingBox(0.0, 0.0, 90.0, 90.0),
        Path(tmp_path),
    )
