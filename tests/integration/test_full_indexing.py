from pathlib import Path

from static_osm_indexer import list_named_locations
from static_osm_indexer import index_locations_names


def test_generate_index(tmp_path):
    names_file: Path = tmp_path / "results.jsonl"
    list_named_locations.dump_location_names(
        "tests/static/test_area.pbf", names_file, ["name"]
    )
    assert names_file.exists()
    with open(names_file) as fr:
        assert len(fr.read().split("\n")) == 833
    # named location list created, now create the index
    output_folder: Path = tmp_path / "output"
    output_folder.mkdir()
    index_locations_names.index_location_names(names_file, output_folder, 3, "")
    assert (output_folder / "fer.json").exists()
