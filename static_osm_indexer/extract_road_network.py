"""
Pyosmium docs: https://docs.osmcode.org/pyosmium/latest/index.html
"""
import logging
from pathlib import Path
import sqlite3
from time import time

import click
from geopy.distance import geodesic
import osmium as o

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# how many nodes to keep in memory before dumping to SQLLite
DUMP_THRESHOLD = 300_000
# how many edges to examine to look for near nodes
# nodes more distant on the graph than this will not be collapsed even when close
COLLAPSE_EDGE_DISTANCE = 5


class RoadNetworkHandler(o.SimpleHandler):
    def __init__(
        self,
        conn: sqlite3.Connection,
        walk: bool,
        bicycle: bool,
        car: bool,
        collapse_distance: float,
    ) -> None:
        super(RoadNetworkHandler, self).__init__()
        self.do_walk = walk
        self.do_bicycle = bicycle
        self.do_car = car

        self.all_nodes: dict[int, tuple[float, float]] = {}
        self.walk_edges: set[tuple[int, int]] = set()
        self.bicycle_edges: set[tuple[int, int]] = set()
        self.car_edges: set[tuple[int, int]] = set()
        self.collapse_nodes: dict[int, int] = {}
        self.processed_ways: int = 0
        self.latest_message: float = time()
        self.conn = conn
        self.collapse_distance = collapse_distance

    def dump_pending_to_db(self) -> None:
        """Dump data from memory to SQLLite."""
        cur = self.conn.cursor()
        cur.executemany(
            """
            INSERT INTO nodes(id, lat, lon)
            VALUES(?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """,
            [(osm_id, lat, lon) for osm_id, (lat, lon) in self.all_nodes.items()],
        )
        self.all_nodes.clear()
        upsert_targets = []
        if self.do_walk:
            upsert_targets.append(("walk_edges", self.walk_edges))
        if self.do_bicycle:
            upsert_targets.append(("bicycle_edges", self.bicycle_edges))
        if self.do_car:
            upsert_targets.append(("car_edges", self.car_edges))
        for table_name, data in upsert_targets:
            cur.executemany(
                f"""
                    INSERT INTO {table_name}(from_id, to_id)
                    VALUES(?, ?)
                    ON CONFLICT (from_id, to_id) DO NOTHING
                """,
                data,
            )
            data.clear()
        if self.collapse_distance > 0.0:
            cur.executemany(
                """
                    INSERT INTO collapse_nodes(id_to_prune, id_to_use)
                    VALUES(?, ?)
                    ON CONFLICT (id_to_prune) DO NOTHING
                """,
                self.collapse_nodes.items(),
            )
            self.collapse_nodes.clear()
        self.conn.commit()

    def way(self, w: o.Way) -> None:  # type: ignore [name-defined]
        # this is only for streets, no buildings or other stuff
        if "highway" not in w.tags:
            return
        # special accesses to ignore
        # see https://taginfo.openstreetmap.org/keys/access#values
        if w.tags.get("access") in (
            "private",
            "no",
            "agricultural",
            "delivery",
            "military",
            "emergency",
        ):
            return
        self.processed_ways += 1
        if time() > self.latest_message + 60:
            logger.debug(f"Processed {self.processed_ways} ways so far...")
            self.latest_message = time()
        if len(self.all_nodes) > DUMP_THRESHOLD:
            logger.debug("Dumping to DB...")
            self.dump_pending_to_db()
            logger.debug("Dumped to DB")

        # now we figure out the direction and access for different vehicles
        # start by assuming everyone can use it, and change if needed
        walk = True
        # direction restrictions on walk are super rare
        # here just for consistency
        walk_back = True
        bicycle = True
        bicycle_back = True
        car = True
        car_back = True
        if w.tags.get("oneway") == "yes":
            walk_back = False
            bicycle_back = False
            car_back = False
        # rare (0.14%)
        if w.tags.get("oneway") == "-1":
            walk = False
            bicycle = False
            car = False
        if w.tags.get("oneway:bicycle") == "yes":
            bicycle_back = False
        if w.tags.get("oneway:bicycle") == "-1":
            bicycle = False
        if w.tags.get("highway") == "footway":
            bicycle = False
            bicycle_back = False
            car = False
            car_back = False
        if w.tags.get("highway") == "motorway":
            walk = False
            walk_back = False
            bicycle = False
            bicycle_back = False
        if w.tags.get("highway") == "cycleway":
            car = False
            car_back = False
        if w.tags.get("foot") in ("yes", "designated"):
            walk = True
            walk_back = True
        if w.tags.get("bicycle") in ("yes", "designated"):
            bicycle = True
            bicycle_back = True
        if w.tags.get("foot") in ("no", "use_sidepath"):
            walk = False
            walk_back = False
        if not (
            (self.do_walk and (walk or walk_back))
            or (self.do_bicycle and (bicycle or bicycle_back))
            or (self.do_car and (car or car_back))
        ):
            # this edge is unused in any covered use case, ignore it
            return
        # w.id # is the OSM way id
        # if w.is_closed() the last node is already repeated
        # no extra logic needed here
        all_nodes = list(w.nodes)
        for from_n, to_n in zip(all_nodes[:-1], all_nodes[1:]):
            if self.do_walk:
                if walk:
                    self.walk_edges.add((from_n.ref, to_n.ref))
                if walk_back:
                    self.walk_edges.add((to_n.ref, from_n.ref))
            if self.do_bicycle:
                if bicycle:
                    self.bicycle_edges.add((from_n.ref, to_n.ref))
                if bicycle_back:
                    self.bicycle_edges.add((to_n.ref, from_n.ref))
            if self.do_car:
                if car:
                    self.car_edges.add((from_n.ref, to_n.ref))
                if car_back:
                    self.car_edges.add((to_n.ref, from_n.ref))

            self.all_nodes[from_n.ref] = (from_n.lat, from_n.lon)
            self.all_nodes[to_n.ref] = (to_n.lat, to_n.lon)
        # avoid checking distances when there's no collapse distance
        if self.collapse_distance <= 0.0:
            return
        # try all combinations of nodes up to 5
        # and the more we collapse the better will be later. Let's be brutal!
        # NOTE: we cannot collapse on the fly, because the OSM id may be used
        # by other ways we'll process later, we must store the collapse ids
        # and apply after all edges have been ingested
        for idx_a in range(len(all_nodes)):
            for idx_b in range(
                idx_a + 1, min(len(all_nodes), len(all_nodes) + COLLAPSE_EDGE_DISTANCE)
            ):
                node_a = all_nodes[idx_a]
                node_b = all_nodes[idx_b]
                # do not collapse points on the same id (loops)
                if node_a.ref == node_b.ref:
                    continue
                if (
                    geodesic((node_a.lat, node_a.lon), (node_b.lat, node_b.lon)).m
                    < self.collapse_distance
                ):
                    # as a convention, collapse to the lower OSM id
                    self.collapse_nodes[max(node_a.ref, node_b.ref)] = min(
                        node_a.ref, node_b.ref
                    )

    def node(self, n: o.Node) -> None:  # type: ignore [name-defined]
        # Already used from way
        pass

    def area(self, a: o.Area) -> None:  # type: ignore [name-defined]
        # TODO how to handle areas? a thing like a walkable square should
        # be part of the navigation?
        pass

    def relation(self, r):  # type: ignore
        # Should not be relevant for this use case
        pass


def extract_road_network(
    input_pbf: str,
    conn: sqlite3.Connection,
    walk: bool,
    bicycle: bool,
    car: bool,
    collapse_distance: float,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE nodes(
        id               INTEGER PRIMARY KEY,
        lat              FLOAT,
        lon              FLOAT
        )"""
    )
    if collapse_distance > 0.0:
        cur.execute(
            """CREATE TABLE collapse_nodes(
            id_to_prune    INTEGER PRIMARY KEY,
            id_to_use    INTEGER
            )"""
        )
    vehicles: list[str] = []
    if walk:
        vehicles.append("walk")
    if bicycle:
        vehicles.append("bicycle")
    if car:
        vehicles.append("car")
    for vehicle in vehicles:
        cur.execute(
            f"""CREATE TABLE {vehicle}_edges(
        from_id    INTEGER,
        to_id      INTEGER,
        PRIMARY KEY (from_id, to_id)
        )"""
        )

    conn.commit()
    rnh = RoadNetworkHandler(conn, walk, bicycle, car, collapse_distance)
    # As we need the geometry, the node locations need to be cached. Therefore
    # set 'locations' to true.
    rnh.apply_file(input_pbf, locations=True)
    # the handler does not know when it's reading the last object
    # must be invoked afterwards to dump the pending
    rnh.dump_pending_to_db()
    logger.info(f"Processed {rnh.processed_ways} ways")
    if collapse_distance > 0.0:
        cur = conn.cursor()
        logger.info("Removing indirect pruning")
        cur.execute(
            """
        delete from collapse_nodes
        where id_to_use in (
            select id_to_prune from collapse_nodes
            )"""
        )
        logger.info("Deleting collapsed nodes")
        cur.execute(
            """
            delete from nodes
            where id in (select id_to_prune from collapse_nodes)
        """
        )
        for vehicle in vehicles:
            logger.info(f"Creating new table for {vehicle}...")
            cur.execute(
                f"""
            create table {vehicle}_edges_new(
                from_id integer,
                to_id integer,
                primary key (from_id, to_id)
            );
            """
            )
            cur.execute(
                f"""
            insert into {vehicle}_edges_new
            select distinct coalesce(cn_f.id_to_use, e.from_id) as from_id,
                            coalesce(cn_t.id_to_use, e.to_id)   as to_id
            from {vehicle}_edges e
                    left join collapse_nodes cn_f
                            ON cn_f.id_to_prune = e.from_id
                    left join collapse_nodes cn_t
                            ON cn_t.id_to_prune = e.to_id
            -- ignore self loops generated by collapsing
            where coalesce(cn_f.id_to_use, e.from_id) <> coalesce(cn_t.id_to_use, e.to_id);
            """
            )
            logger.info("Replacing the old table")
            cur.execute(f"drop table {vehicle}_edges;")
            cur.execute(f"alter table {vehicle}_edges_new rename to {vehicle}_edges")
        conn.commit()


@click.command()
@click.argument("input_pbf", type=click.Path(exists=True, dir_okay=False))
@click.argument(
    "output_folder",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
)
@click.option("--walk/--no-walk", default=True)
@click.option("--bicycle/--no-bicycle", default=True)
@click.option("--car/--no-car", default=True)
@click.option("--car/--no-car", default=True)
@click.option(
    "--collapse-distance",
    type=click.FLOAT,
    default=0,
    help="Distance in meters between points under which they are collapsed",
)
def main(
    input_pbf: str,
    output_folder: Path,
    walk: bool,
    bicycle: bool,
    car: bool,
    collapse_distance: float,
) -> None:
    if not output_folder.exists():
        output_folder.mkdir()
    conn = sqlite3.connect(str(output_folder / "network.db"))
    extract_road_network(input_pbf, conn, walk, bicycle, car, collapse_distance)


if __name__ == "__main__":
    main()
