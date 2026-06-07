# Asset loading
from __future__ import annotations

from pathlib import Path

import pygame

from settings import PLAYER_SIZE, TILE_SIZE

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

TILE_KEYS = {
    "hub.floor": "tiles/hub/floor.png",
    "hub.wall": "tiles/hub/wall.png",
    "hub.portal": "tiles/hub/portal.png",
    "hub.lunar_gate_off": "tiles/common/lunar_gate_off.png",
    "hub.lunar_gate_on": "tiles/common/lunar_gate_on.png",
    "hub.warp_gate_off": "tiles/common/warp_gate_off.png",
    "hub.warp_gate_on": "tiles/common/warp_gate_on.png",
    "selene.floor": "tiles/selene/floor.png",
    "selene.wall": "tiles/selene/wall.png",
    "selene.portal": "tiles/selene/portal.png",
    "selene.relic": "tiles/selene/relic.png",
    "selene.hazard": "tiles/selene/hazard.png",
    "nyx.floor": "tiles/nyx/floor.png",
    "nyx.wall": "tiles/nyx/wall.png",
    "nyx.portal": "tiles/nyx/portal.png",
    "nyx.relic": "tiles/nyx/relic.png",
    "nyx.switch": "tiles/nyx/switch.png",
    "nyx.barrier": "tiles/nyx/barrier.png",
    "eos.floor": "tiles/eos/floor.png",
    "eos.wall": "tiles/eos/wall.png",
    "eos.portal": "tiles/eos/portal.png",
    "eos.relic": "tiles/eos/relic.png",
    "eos.switch": "tiles/eos/switch.png",
    "eos.barrier": "tiles/eos/barrier.png",
}

BG_KEYS = {
    "bg.hub": "backgrounds/hub.png",
    "bg.selene": "backgrounds/selene.png",
    "bg.nyx": "backgrounds/nyx.png",
    "bg.eos": "backgrounds/eos.png",
}


class AssetLibrary:
    def __init__(self) -> None:
        self.images: dict[str, pygame.Surface] = {}
        self._raw: dict[str, pygame.Surface] = {}
        self._scaled_cache: dict[tuple[str, int, int], pygame.Surface] = {}
        self._load()

    def _safe_load(self, relative_path: str):
        candidates = [relative_path]
        if relative_path.endswith("warp_gate_off.png"):
            candidates.append(relative_path.replace("warp_gate_off.png", "wapp_gate_off.png"))
        for cand in candidates:
            path = ASSETS_DIR / cand
            if path.exists():
                return pygame.image.load(str(path)).convert_alpha()
        return None

    def _load(self) -> None:
        sprite = self._safe_load("player/bean_idle.png")
        if sprite is not None:
            self.images["player.bean"] = pygame.transform.smoothscale(sprite, (PLAYER_SIZE, PLAYER_SIZE))

        for key, rel in TILE_KEYS.items():
            img = self._safe_load(rel)
            if img is not None:
                self.images[key] = pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE))

        for key, rel in BG_KEYS.items():
            img = self._safe_load(rel)
            if img is not None:
                self._raw[key] = img

    def get(self, key: str):
        return self.images.get(key)

    def get_background(self, name: str, width: int, height: int):
        key = f"bg.{name}"
        if key not in self._raw:
            return None
        cache_key = (key, width, height)
        if cache_key not in self._scaled_cache:
            self._scaled_cache[cache_key] = pygame.transform.smoothscale(self._raw[key], (width, height))
        return self._scaled_cache[cache_key]
