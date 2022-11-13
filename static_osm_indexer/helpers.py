from dataclasses import dataclass


@dataclass
class BoundingBox:
    minlon: float
    minlat: float
    maxlon: float
    maxlat: float

    def __str__(self) -> str:
        return f"{self.minlon},{self.minlat},{self.maxlon},{self.maxlat}"
