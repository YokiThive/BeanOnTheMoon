"""Level layouts and moon configuration.

Tile legend
-----------
  #  wall                         R  relic (locked until guardian is defeated)
  .  floor                        B  guardian spawn (mini-boss)
  S  player spawn                 c  chaser enemy spawn
  1  hub portal -> Selene         p  patroller enemy spawn
  2  hub portal -> Nyx            *  star fragment (optional collectible)
  3  hub portal -> Eos            +  health pickup
  H  portal back to the hub       K  key pickup
  G  Lunar Gate (hub)             D  locked door (opens by spending a key)
  W  Warp Gate (hub)              s  switch (all switches open the x barriers)
  C  checkpoint                   x  barrier (solid until every switch is on)
                                  ^  spike trap (walkable, damages on contact)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LevelTemplate:
    title: str
    floor_color: tuple[int, int, int]
    wall_color: tuple[int, int, int]
    portal_color: tuple[int, int, int]
    relic_color: tuple[int, int, int]
    intro: str
    layout: list[str]


HUB_LAYOUT = [
    '##############################',
    '#............................#',
    '#............................#',
    '#......1..............2......#',
    '#............................#',
    '#............................#',
    '#...####..........####.......#',
    '#............................#',
    '#.............G..............#',
    '#............................#',
    '#............................#',
    '#............S...............#',
    '#............................#',
    '#.......####......####.......#',
    '#............................#',
    '#.............3..............#',
    '#............................#',
    '#.............W..............#',
    '#............................#',
    '##############################',
]

SELENE_LAYOUT = [
    '##############################',
    '#S.....^......*.......c......#',
    '#..####.......^....####......#',
    '#.....#.......^.......#..*...#',
    '#..*..#.............#........#',
    '#.....#####....#####.........#',
    '#.........s..................#',
    '######.####........####.######',
    '#........#....c....#.........#',
    '#...K....#.........#....*....#',
    '#........####xx#####.........#',
    '#........#.........#.........#',
    '#...p....#....B....#....s....#',
    '#........#.........#.........#',
    '######.###############.#######',
    '#..........p.......#.........#',
    '#..*..D............#...^.....#',
    '#.....####....####.#.....+...#',
    '#H..............R...........*#',
    '##############################',
]

NYX_LAYOUT = [
    '##############################',
    '#S...........c...........*...#',
    '#...####............####.....#',
    '#...#..........s.......#.....#',
    '#...#....*.............#..c..#',
    '#...######.......######......#',
    '#................#...........#',
    '#....c......######....+......#',
    '#..........#......#..........#',
    '#....K.....#..B...#....*.....#',
    '#..........#......#..........#',
    '#####.######xxxx###.....######',
    '#.........#......#...........#',
    '#...*.....#..c...#....s......#',
    '#.........D......#...........#',
    '#######.######.######..#######',
    '#..........................c.#',
    '#..+...*.........^.....*.....#',
    '#H..............R...........*#',
    '##############################',
]

EOS_LAYOUT = [
    '##############################',
    '#S....^....c.....^....*......#',
    '#..#####........#####........#',
    '#......#...*....#....#...c...#',
    '#..s...#.......^#....#.......#',
    '#......#########....##....^..#',
    '#..........c.......s.........#',
    '####.#######...#######.#.#####',
    '#......#.........#....#...*..#',
    '#..K...#....c....#..c.#......#',
    '#......#.........#....#......#',
    '#......####xxxx###....#......#',
    '#..*...#.........#....D......#',
    '#......#....B....#....#..+...#',
    '####.###############.##.######',
    '#........^....^.....^........#',
    '#..*..p.........p........*...#',
    '#....####.....####....####...#',
    '#H..........R...............*#',
    '##############################',
]


LEVEL_TEMPLATES = {
    "hub": LevelTemplate(
        title="Ancient Hub",
        floor_color=(62, 68, 96),
        wall_color=(150, 158, 196),
        portal_color=(126, 222, 255),
        relic_color=(255, 255, 255),
        intro="Three portals, three guarded moons. Bring back all three relics.",
        layout=HUB_LAYOUT,
    ),
    "selene": LevelTemplate(
        title="Selene",
        floor_color=(86, 96, 138),
        wall_color=(206, 214, 236),
        portal_color=(180, 231, 255),
        relic_color=(216, 243, 255),
        intro="Selene: flip both shard switches, beat the Frost Warden, take the relic.",
        layout=SELENE_LAYOUT,
    ),
    "nyx": LevelTemplate(
        title="Nyx",
        floor_color=(48, 34, 78),
        wall_color=(132, 110, 176),
        portal_color=(204, 133, 255),
        relic_color=(230, 154, 255),
        intro="Nyx: phantoms roam the dark. Open the seals and break the Shade Keeper.",
        layout=NYX_LAYOUT,
    ),
    "eos": LevelTemplate(
        title="Eos",
        floor_color=(104, 66, 34),
        wall_color=(230, 184, 110),
        portal_color=(255, 191, 103),
        relic_color=(255, 234, 134),
        intro="Eos: the hottest moon. Solar flares, switches, and the Sun Tyrant await.",
        layout=EOS_LAYOUT,
    ),
}

PORTAL_DESTINATIONS = {
    "1": "selene",
    "2": "nyx",
    "3": "eos",
}

# Tiles that block movement (doors/barriers are removed from the grid when opened).
SOLID_TILES = {"#", "D", "x"}
