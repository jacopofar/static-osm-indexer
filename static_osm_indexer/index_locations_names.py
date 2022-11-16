import json
import logging
from pathlib import Path
import re
from typing import Any

import click

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def dump_names(
    pending: dict[str, list[dict[str, Any]]], name_indexes_folder: Path
) -> None:
    """Append the names to the files, preserving what's already in there."""
    for prefix, addresses in pending.items():
        target_file = name_indexes_folder / f"{prefix}.json"
        addresses_list = []
        if target_file.exists():
            with open(target_file) as fr:
                addresses_list = json.load(fr)

        addresses_list.extend(addresses)
        with open(target_file, "w") as fw:
            json.dump(addresses_list, fw, indent=2)


def index_location_names(
    input_locations_list: str,
    output_folder: Path,
    token_length: int,
    stopwords: set[str],
) -> None:
    logger.debug(f"Will index with token length {token_length}")
    logger.debug(f"Ignoring tokens: {stopwords}")
    pending: dict[str, list[dict[str, Any]]] = {}
    SPLIT = re.compile(r"[^\w]+")
    MAX_PENDING = 10000
    with open(input_locations_list) as fr:
        for idx, line in enumerate(fr):
            addr = json.loads(line)
            parts = re.split(SPLIT, addr["name"].lower())
            for p in parts:
                # ignore this word for reverse index
                # this works ONLY if we assume the word can never appear as a proper name
                # so for example "Folsom street" is OK but there's no "street street"
                if p in stopwords:
                    continue
                if len(p) >= token_length:
                    if p[:token_length] in pending:
                        pending[p[:token_length]].append(addr)
                    else:
                        pending[p[:token_length]] = [addr]
            if len(pending) > MAX_PENDING:
                logger.debug(f"Writing addresses {idx}")
                dump_names(pending, output_folder)
                pending = {}
    dump_names(pending, output_folder)
    with open(output_folder / "index_metadata.json", "w") as fw:
        json.dump(
            dict(
                stopwords=list(stopwords),
                token_length=token_length,
            ),
            fw,
            indent=2,
        )
    logger.debug(f"Processed {idx} lines")


def validate_stopwords(
    ctx: click.Context, param: click.Parameter, value: str
) -> set[str]:
    if not isinstance(value, str):
        raise click.BadParameter(f"must be a string, it was {type(value)}")
    words = [w.strip() for w in value.split(",")]
    return set(words)


@click.command()
@click.argument("input_locations_list", type=click.Path(exists=True, dir_okay=False))
@click.argument(
    "output_folder",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path),
)
@click.option(
    "--token_length",
    default=3,
    show_default=True,
    type=click.INT,
    help="Length of the prefix for the reverse index",
)
@click.option(
    "--stopwords",
    default="",
    show_default=True,
    type=click.STRING,
    callback=validate_stopwords,
    help="Comma separated list of words not to be indexed. Case insensitive.",
)
def main(
    input_locations_list: str,
    output_folder: Path,
    token_length: int,
    stopwords: set[str],
) -> None:
    index_location_names(input_locations_list, output_folder, token_length, stopwords)


if __name__ == "__main__":
    main()
