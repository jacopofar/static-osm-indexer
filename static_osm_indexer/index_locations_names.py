import json
from pathlib import Path
import re

import click


def dump_names(pending, name_indexes_folder):
    for prefix, addresses in pending.items():
        target_file = name_indexes_folder / f"{prefix}.json"
        addresses_list = []
        if target_file.exists():
            with open(target_file) as fr:
                addresses_list = json.load(fr)

        addresses_list.extend(addresses)
        with open(target_file, "w") as fw:
            json.dump(addresses_list, fw, indent=2)


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
    help="Comma separated list of words not to be indexed. Case insensitive.",
)
def main(
    input_locations_list: str, output_folder: Path, token_length: int, stopwords: str
):
    pending: dict[str, list[dict]] = {}
    SPLIT = re.compile(r"[^\w]+")
    MAX_PENDING = 10000
    skip = stopwords.split(",")
    with open(input_locations_list) as fr:
        for idx, line in enumerate(fr):
            addr = json.loads(line)
            parts = re.split(SPLIT, addr["name"].lower())
            for p in parts:
                # ignore this word for reverse index
                # this works ONLY if we assume the word can never appear as a proper name
                # so for example "Folsom street" is OK but there's no "street street"
                if p in skip:
                    continue
                if len(p) >= token_length:
                    if p[:token_length] in pending:
                        pending[p[:token_length]].append(addr)
                    else:
                        pending[p[:token_length]] = [addr]
            if len(pending) > MAX_PENDING:
                print(f"Writing addresses {idx}")
                dump_names(pending, output_folder)
                pending = {}
    dump_names(pending, output_folder)
    with open(output_folder / "index_metadata.json", "w") as fw:
        json.dump(
            dict(
                stopwords=stopwords,
                token_length=token_length,
            ),
            fw,
            indent=2,
        )
    print(f"Processed {idx} lines")


if __name__ == "__main__":
    main()
