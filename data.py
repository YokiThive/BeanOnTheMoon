# Level metadata. Layouts are loaded from levels/<name>.tmx
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tile_loader import load_tmx

LEVELS_DIR = Path(__file__).resolve().parent / "levels"


@dataclass(frozen=True)
class LevelTemplate:
    title: str
    floor_color: tuple[int, int, int]
    wall_color: tuple[int, int, int]
    portal_color: tuple[int, int, int]
    relic_color: tuple[int, int, int]
    intro: str
    layout: list[str]


def _level(name, **meta):
    return LevelTemplate(layout=load_tmx(LEVELS_DIR / f"{name}.tmx"), **meta)


LEVEL_TEMPLATES = {
    "hub": _level(
        "hub",
        title="Ancient Hub",
        floor_color=(62, 68, 96),
        wall_color=(150, 158, 196),
        portal_color=(126, 222, 255),
        relic_color=(255, 255, 255),
        intro="Three portals, three guarded moons. Bring back all three relics.",
    ),
    "selene": _level(
        "selene",
        title="Selene",
        floor_color=(86, 96, 138),
        wall_color=(206, 214, 236),
        portal_color=(180, 231, 255),
        relic_color=(216, 243, 255),
        intro="Selene: flip both shard switches, beat the Frost Warden, take the relic.",
    ),
    "nyx": _level(
        "nyx",
        title="Nyx",
        floor_color=(48, 34, 78),
        wall_color=(132, 110, 176),
        portal_color=(204, 133, 255),
        relic_color=(230, 154, 255),
        intro="Nyx: phantoms roam the dark. Open the seals and break the Shade Keeper.",
    ),
    "eos": _level(
        "eos",
        title="Eos",
        floor_color=(104, 66, 34),
        wall_color=(230, 184, 110),
        portal_color=(255, 191, 103),
        relic_color=(255, 234, 134),
        intro="Eos: the hottest moon. Solar flares, switches, and the Sun Tyrant await.",
    ),
}

PORTAL_DESTINATIONS = {
    "1": "selene",
    "2": "nyx",
    "3": "eos",
}

SOLID_TILES = {"#", "D", "x"}
