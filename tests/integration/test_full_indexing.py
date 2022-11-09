from pathlib import Path

from static_osm_indexer import list_named_locations
from static_osm_indexer import index_locations_names


def test_generate_index(tmp_path, pbf_input_sample):
    names_file: Path = tmp_path / "results.jsonl"
    list_named_locations.dump_location_names(pbf_input_sample, names_file, ["name"])

    # named location list created, now create the index
    output_folder: Path = tmp_path / "output"
    output_folder.mkdir()
    index_locations_names.index_location_names(names_file, output_folder, 3, "")
    assert (output_folder / "fer.json").exists()
