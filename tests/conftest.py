import pytest


@pytest.fixture(scope="session")
def pbf_input_sample():
    return "tests/static/test_area.pbf"
