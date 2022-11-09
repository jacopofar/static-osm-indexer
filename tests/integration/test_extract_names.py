from pathlib import Path

from static_osm_indexer import list_named_locations


def test_extract_name(tmp_path, pbf_input_sample):
    names_file: Path = tmp_path / "results.jsonl"
    list_named_locations.dump_location_names(pbf_input_sample, names_file, ["name"])
    assert names_file.exists()
    with open(names_file) as fr:
        assert len(fr.readlines()) == 832


def test_extract_name_in_locale(tmp_path, pbf_input_sample):
    names_file: Path = tmp_path / "results.jsonl"
    list_named_locations.dump_location_names(pbf_input_sample, names_file, ["name:en"])
    assert names_file.exists()
    with open(names_file) as fr:
        assert len(fr.readlines()) == 4
