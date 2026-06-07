# Load Tiled .tmx maps into list-of-strings layouts
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

GID_MASK = 0x1FFFFFFF


def _load_tsx(tsx_path: Path) -> dict[int, str]:
    root = ET.parse(tsx_path).getroot()
    mapping: dict[int, str] = {}
    for tile in root.findall("tile"):
        tid = int(tile.attrib["id"])
        props = tile.find("properties")
        if props is None:
            continue
        for prop in props.findall("property"):
            if prop.attrib.get("name") == "char":
                mapping[tid] = prop.attrib["value"]
                break
    if not mapping:
        raise ValueError(f"{tsx_path}: no tiles had a 'char' property")
    return mapping


def load_tmx(tmx_path: str | Path) -> list[str]:
    tmx_path = Path(tmx_path)
    root = ET.parse(tmx_path).getroot()
    width = int(root.attrib["width"])
    height = int(root.attrib["height"])

    ts = root.find("tileset")
    if ts is None:
        raise ValueError(f"{tmx_path}: no <tileset> element")
    firstgid = int(ts.attrib.get("firstgid", "1"))
    source = ts.attrib.get("source")
    if not source:
        raise ValueError(f"{tmx_path}: only external tilesets are supported")
    tsx_path = (tmx_path.parent / source).resolve()
    char_map = _load_tsx(tsx_path)

    layer = root.find("layer")
    if layer is None:
        raise ValueError(f"{tmx_path}: no <layer> element")
    data = layer.find("data")
    if data is None or data.text is None:
        raise ValueError(f"{tmx_path}: layer has no data")
    encoding = data.attrib.get("encoding", "csv")
    if encoding != "csv":
        raise ValueError(f"{tmx_path}: only CSV encoding is supported (got {encoding!r})")

    raw = data.text.replace("\n", "").replace(" ", "")
    gids = [int(x) for x in raw.split(",") if x]
    if len(gids) != width * height:
        raise ValueError(f"{tmx_path}: expected {width*height} cells, got {len(gids)}")

    rows: list[str] = []
    for ry in range(height):
        chars = []
        for cx in range(width):
            gid = gids[ry * width + cx] & GID_MASK
            local_id = gid - firstgid
            chars.append(char_map.get(local_id, "."))
        rows.append("".join(chars))
    return rows
