"""
Pyosmium docs: https://docs.osmcode.org/pyosmium/latest/index.html
"""
import logging
import json
from pathlib import Path
import sqlite3
from io import TextIOWrapper
import click

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def store_edges_into_geojson(
    conn: sqlite3.Connection, fw: TextIOWrapper, walk: bool, bicycle: bool, car: bool
) -> None:
    cur = conn.cursor()

    to_read = []
    if walk:
        to_read.append("walk")
    if bicycle:
        to_read.append("bicycle")
    if car:
        to_read.append("car")
    query = " UNION ALL ".join(
        f"""
        select nf.lat, nf.lon, nt.lat, nt.lon
            from {vehicle}_edges e
         join nodes nf
              ON e.from_id = nf.id
         join nodes nt
              ON e.to_id = nt.id
        """
        for vehicle in to_read
    )
    fw.write(
        """{
        "type": "FeatureCollection",
        "features": [
    """
    )
    edges_repr: list[str] = []
    for (flat, flon, tlat, tlon) in cur.execute(query):
        edges_repr.append(
            json.dumps(
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "coordinates": [
                            [flon, flat],
                            [tlon, tlat],
                        ],
                        "type": "LineString",
                    },
                }
            )
        )
    fw.write(", \n".join(edges_repr))
    fw.write("]}")


def store_nodes_into_geojson(
    conn: sqlite3.Connection, fw: TextIOWrapper, walk: bool, bicycle: bool, car: bool
) -> None:
    cur = conn.cursor()

    to_read = []
    if walk:
        to_read.append("walk")
    if bicycle:
        to_read.append("bicycle")
    if car:
        to_read.append("car")
    query = " UNION ALL ".join(
        f"""
        select distinct n.lat, n.lon
        from {vehicle}_edges e
            join nodes n
              ON e.from_id = n.id
              OR e.to_id = n.id

        """
        for vehicle in to_read
    )
    fw.write(
        """{
        "type": "FeatureCollection",
        "features": [
    """
    )
    nodes_repr: list[str] = []
    for (lat, lon) in cur.execute(query):
        nodes_repr.append(
            json.dumps(
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {"coordinates": [lon, lat], "type": "Point"},
                }
            )
        )
    fw.write(", \n".join(nodes_repr))
    fw.write("]}")


@click.command()
@click.argument(
    "target_folder",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
)
@click.option("--walk/--no-walk", default=True)
@click.option("--bicycle/--no-bicycle", default=True)
@click.option("--car/--no-car", default=True)
def main(target_folder: Path, walk: bool, bicycle: bool, car: bool) -> None:
    conn = sqlite3.connect(str(target_folder / "network.db"))
    with open(target_folder / "edges.json", "w") as fw:
        store_edges_into_geojson(conn, fw, walk, bicycle, car)
    with open(target_folder / "nodes_only.json", "w") as fw:
        store_nodes_into_geojson(conn, fw, walk, bicycle, car)


if __name__ == "__main__":
    main()
