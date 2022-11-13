from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def pbf_input_sample():
    return Path("tests/static/test_area.pbf")
