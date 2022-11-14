"""
Pyosmium docs: https://docs.osmcode.org/pyosmium/latest/index.html
"""
from io import TextIOWrapper
import json
import logging
from time import time

import click
import osmium as o
import shapely.wkb as wkblib

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

NamedLocation = tuple[str, float, float]


class NameHandler(o.SimpleHandler):
    def __init__(self, target_file: TextIOWrapper, tags: list[str]):
        super(NameHandler, self).__init__()
        self.target_file = target_file
        self.invalid_counter = 0
        self.total_names = 0
        self.tags = tags
        self.wkbfab = o.geom.WKBFactory()
        self.latest_message: float = time()

    def handle_named_point(self, name: str, lon: float, lat: float) -> None:
        self.target_file.write(
            json.dumps(dict(name=name, lat=lat, lon=lon), ensure_ascii=False)
        )
        self.target_file.write("\n")
        self.total_names += 1
        if time() > self.latest_message + 60:
            logger.debug(f"Extracted {self.total_names} so far...")
            self.latest_message = time()

    def way(self, w: o.Way) -> None:  # type: ignore [name-defined]
        if w.is_closed():
            # will appear as area, ignore here
            return
        named_locations: set[NamedLocation] = set()
        for tag_name in self.tags:
            if tag_name in w.tags:
                try:
                    wkb = self.wkbfab.create_linestring(w)
                except o.InvalidLocationError:
                    logger.warn(f"Ignoring way {w} because it's invalid")
                    self.invalid_counter += 1
                    return
                except RuntimeError as e:
                    if "need at least two points for linestring" in str(e):
                        logger.warn(f"Ignoring way {w} because points are missing")
                        self.invalid_counter += 1
                        return
                poly = wkblib.loads(wkb, hex=True)
                centroid = poly.representative_point()
                tag_value = w.tags.get(tag_name)
                assert tag_value is not None
                named_locations.add((tag_value, centroid.x, centroid.y))
        for name, x, y in named_locations:
            self.handle_named_point(name, x, y)

    def node(self, n: o.Node) -> None:  # type: ignore [name-defined]
        named_locations: set[NamedLocation] = set()
        for tag_name in self.tags:
            if tag_name in n.tags:
                tag_value = n.tags.get(tag_name)
                assert tag_value is not None
                named_locations.add((tag_value, n.location.lon, n.location.lat))
        for name, x, y in named_locations:
            self.handle_named_point(name, x, y)

    # areas are "synthetic" objects corresponding to some existing osm object
    # https://osmcode.org/osmium-concepts/#areas
    # also notice the same object will appear as relation or way
    # the opposite is NOT true. A relation has many ways inside (holes and/or multipolygon), and they will
    # appear here as ways but only once as areas, which is usually what we want
    # so unless the ids of relations are needed separately, area can replace relations and closed ways (w.is_closed())
    def area(self, a: o.Area) -> None:  # type: ignore [name-defined]
        named_locations: set[NamedLocation] = set()
        for tag_name in self.tags:
            if tag_name in a.tags:
                try:
                    wkb = self.wkbfab.create_multipolygon(a)
                except RuntimeError as e:
                    if "invalid area" in str(e):
                        logger.warn(
                            f"Invalid area {a} from OSM id {a.orig_id()}, ignored"
                        )
                        return
                    else:
                        raise e

                poly = wkblib.loads(wkb, hex=True)
                centroid = poly.representative_point()
                tag_value = a.tags.get(tag_name)
                assert tag_value is not None
                named_locations.add((tag_value, centroid.x, centroid.y))
        for name, x, y in named_locations:
            self.handle_named_point(name, x, y)

    def relation(self, r):  # type: ignore
        # Relations not already visible as area objects are things not useful
        # as named locations
        # using `osmium show`` it's possible to see them, in the test file
        # there are many that represents for example the M5 line or the whole
        # Milan public transport system.
        # this method is defined only to hold for this comment
        pass


def dump_location_names(input_pbf: str, output_file: str, tags: list[str]) -> None:
    with open(output_file, "w") as fw:
        nh = NameHandler(fw, tags)
        # As we need the geometry, the node locations need to be cached. Therefore
        # set 'locations' to true.
        nh.apply_file(input_pbf, locations=True)
    logger.info(f"found {nh.total_names} names")
    logger.info(f"found {nh.invalid_counter} invalid objects")


@click.command()
@click.argument("input_pbf", type=click.Path(exists=True, dir_okay=False))
@click.argument(
    "output_file",
    type=click.Path(file_okay=True, dir_okay=False),
)
@click.option(
    "--tags",
    default="name",
    show_default=True,
    type=click.STRING,
    help="Comma separated list of tags to extract."
    "Identical name and coordinates combinations are deduplicated.",
)
def main(input_pbf: str, output_file: str, tags: str) -> None:
    dump_location_names(input_pbf, output_file, [t.strip() for t in tags.split(",")])


if __name__ == "__main__":
    main()
