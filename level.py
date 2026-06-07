# Level loading, entity management, and rendering
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from data import SOLID_TILES, LevelTemplate
from entities import make_enemy
from settings import (
    DAMAGE_COOLDOWN,
    HEAL_COLOR,
    KEY_COLOR,
    PLAY_HEIGHT,
    PLAY_WIDTH,
    SPIKE_COLOR,
    STAR_COLOR,
    TILE_SIZE,
)

if TYPE_CHECKING:
    from assets import AssetLibrary
    from effects import EffectSystem
    from player import Player

INTERACTABLES = {"1", "2", "3", "H", "G", "W", "R"}
ENEMY_CHARS = {"c": "chaser", "p": "patroller"}


class Level:
    def __init__(self, name: str, template: LevelTemplate, state: dict, relic_collected: bool) -> None:
        self.name = name
        self.template = template
        self.state = state
        self.tiles = [list(row) for row in template.layout]
        self.width = len(self.tiles[0])
        self.height = len(self.tiles)
        self.world_w = self.width * TILE_SIZE
        self.world_h = self.height * TILE_SIZE
        self.anim = 0.0

        self.enemies = []
        self.guardian = None
        self.total_switches = sum(row.count("s") for row in self.tiles)

        state.setdefault("switches", set())
        state.setdefault("keys", 0)
        state.setdefault("door_open", False)
        state.setdefault("barriers_open", False)
        state.setdefault("guardian_dead", False)
        state.setdefault("stars", set())
        state.setdefault("health_taken", set())

        self._apply_state(relic_collected)
        self._spawn_entities()

    def _apply_state(self, relic_collected: bool) -> None:
        # Restore previously pressed switches as pressed markers
        for (tx, ty) in self.state["switches"]:
            if self._in_bounds(tx, ty) and self.tiles[ty][tx] == "s":
                self.tiles[ty][tx] = "o"
        if self.state["barriers_open"]:
            self._replace("x", ".")
        if self.state["door_open"]:
            self._replace("D", ".")
        for (tx, ty) in self.state["stars"]:
            if self._in_bounds(tx, ty) and self.tiles[ty][tx] == "*":
                self.tiles[ty][tx] = "."
        for (tx, ty) in self.state["health_taken"]:
            if self._in_bounds(tx, ty) and self.tiles[ty][tx] == "+":
                self.tiles[ty][tx] = "."
        if relic_collected:
            self._replace("R", ".")

    def _spawn_entities(self) -> None:
        for ty, row in enumerate(self.tiles):
            for tx, ch in enumerate(row):
                if ch in ENEMY_CHARS:
                    self.enemies.append(make_enemy(ENEMY_CHARS[ch], tx, ty))
                    self.tiles[ty][tx] = "."
                elif ch == "B":
                    self.tiles[ty][tx] = "."
                    if not self.state["guardian_dead"]:
                        self.guardian = make_enemy("guardian", tx, ty)

    def _replace(self, old: str, new: str) -> None:
        for row in self.tiles:
            for i, ch in enumerate(row):
                if ch == old:
                    row[i] = new

    @property
    def title(self) -> str:
        return self.template.title

    def _in_bounds(self, tx: int, ty: int) -> bool:
        return 0 <= ty < self.height and 0 <= tx < self.width

    def get_tile(self, tx: int, ty: int) -> str:
        if not self._in_bounds(tx, ty):
            return "#"
        return self.tiles[ty][tx]

    def is_wall_at_pixel(self, px: float, py: float) -> bool:
        return self.get_tile(int(px // TILE_SIZE), int(py // TILE_SIZE)) in SOLID_TILES

    def find_tile(self, target: str) -> tuple[int, int] | None:
        for ty, row in enumerate(self.tiles):
            for tx, ch in enumerate(row):
                if ch == target:
                    return tx, ty
        return None

    def spawn_tile(self) -> tuple[int, int]:
        pos = self.find_tile("S")
        return pos if pos else (1, 1)

    def _tiles_overlapping(self, rect: pygame.FRect):
        x0 = max(0, int(rect.left // TILE_SIZE))
        x1 = min(self.width - 1, int(rect.right // TILE_SIZE))
        y0 = max(0, int(rect.top // TILE_SIZE))
        y1 = min(self.height - 1, int(rect.bottom // TILE_SIZE))
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                yield tx, ty, self.tiles[ty][tx]

    def interaction_near(self, player: "Player") -> tuple[str, int, int] | None:
        cx, cy = player.center
        offsets = [(0, 0), (TILE_SIZE, 0), (-TILE_SIZE, 0), (0, TILE_SIZE), (0, -TILE_SIZE)]
        for ox, oy in offsets:
            tx, ty = int((cx + ox) // TILE_SIZE), int((cy + oy) // TILE_SIZE)
            ch = self.get_tile(tx, ty)
            if ch in INTERACTABLES:
                return ch, tx, ty
        return None

    @property
    def relic_unlocked(self) -> bool:
        return self.state["guardian_dead"]

    def update(self, dt: float, player: "Player", effects: "EffectSystem") -> dict:
        self.anim += dt
        result = {
            "damage": None, "stars": 0, "health": False, "key": False,
            "door": False, "switch": None, "guardian_hit": False,
            "guardian_killed": False, "enemy_killed": 0,
        }
        pcenter = player.center

        # enemies
        for enemy in self.enemies:
            enemy.update(dt, pcenter, self)
        if self.guardian:
            self.guardian.update(dt, pcenter, self)

        # touch-based tiles (pickups / switches / spikes / doors)
        for tx, ty, ch in list(self._tiles_overlapping(player.rect)):
            if ch == "*":
                self.tiles[ty][tx] = "."
                self.state["stars"].add((tx, ty))
                result["stars"] += 1
                effects.burst(*self._tile_center(tx, ty), STAR_COLOR, count=10, speed=160, life=0.5)
            elif ch == "+":
                self.tiles[ty][tx] = "."
                self.state["health_taken"].add((tx, ty))
                result["health"] = True
                effects.ring(*self._tile_center(tx, ty), HEAL_COLOR, count=14, speed=180)
            elif ch == "K":
                self.tiles[ty][tx] = "."
                self.state["keys"] += 1
                result["key"] = True
                effects.burst(*self._tile_center(tx, ty), KEY_COLOR, count=12, speed=180)
            elif ch == "s":
                self.tiles[ty][tx] = "o"
                self.state["switches"].add((tx, ty))
                effects.ring(*self._tile_center(tx, ty), (150, 240, 255), count=16, speed=220)
                if len(self.state["switches"]) >= self.total_switches and not self.state["barriers_open"]:
                    self._replace("x", ".")
                    self.state["barriers_open"] = True
                    result["switch"] = "opened"
                else:
                    result["switch"] = "partial"

        # doors: open if adjacent and holding a key (door tile is solid, so check neighbours)
        if self.state["keys"] > 0 and not self.state["door_open"]:
            if self._door_adjacent(player.rect):
                self._replace("D", ".")
                self.state["keys"] -= 1
                self.state["door_open"] = True
                result["door"] = True

        # spikes (only when standing on one and vulnerable)
        ctx, cty = int(pcenter[0] // TILE_SIZE), int(pcenter[1] // TILE_SIZE)
        if self.get_tile(ctx, cty) == "^" and not player.invulnerable:
            result["damage"] = "A spike trap pierces Bean's suit."

        # combat: dash hits enemies; touching them otherwise hurts Bean
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if enemy.rect.colliderect(player.rect):
                if player.is_dashing:
                    if enemy.take_hit():
                        result["enemy_killed"] += 1
                        effects.burst(*enemy.center, enemy.color, count=18, speed=240, life=0.6)
                elif not player.invulnerable and result["damage"] is None:
                    result["damage"] = "An enemy slams into Bean."
        self.enemies = [e for e in self.enemies if e.alive]

        # guardian combat
        if self.guardian and self.guardian.alive:
            if self.guardian.rect.colliderect(player.rect):
                if player.is_dashing:
                    killed = self.guardian.take_hit()
                    if self.guardian and self.guardian.flash > 0:
                        result["guardian_hit"] = True
                        effects.burst(*self.guardian.center, self.guardian.color, count=12, speed=200)
                    if killed:
                        result["guardian_killed"] = True
                        self.state["guardian_dead"] = True
                        effects.ring(*self.guardian.center, (255, 220, 255), count=28, speed=320)
                        effects.burst(*self.guardian.center, self.guardian.color, count=30, speed=300, life=0.8)
                        self.guardian = None
                elif not player.invulnerable and result["damage"] is None:
                    result["damage"] = "The guardian crashes into Bean."

        return result

    def _door_adjacent(self, rect: pygame.FRect) -> bool:
        probe = rect.inflate(10, 10)
        for _, _, ch in self._tiles_overlapping(probe):
            if ch == "D":
                return True
        return False

    def _tile_center(self, tx: int, ty: int) -> tuple[float, float]:
        return tx * TILE_SIZE + TILE_SIZE / 2, ty * TILE_SIZE + TILE_SIZE / 2

    def _asset_key(self, ch: str, gate_restored: bool) -> str | None:
        if ch == "#":
            return f"{self.name}.wall"
        if ch in {"1", "2", "3"}:
            return "hub.portal"
        if ch == "H":
            return f"{self.name}.portal"
        if ch == "G":
            return "hub.lunar_gate_on" if gate_restored else "hub.lunar_gate_off"
        if ch == "W":
            return "hub.warp_gate_on" if gate_restored else "hub.warp_gate_off"
        if ch == "R":
            return f"{self.name}.relic"
        if ch in {"s", "o"}:
            return f"{self.name}.switch"
        if ch == "x":
            return f"{self.name}.barrier"
        return None

    def draw(self, screen: pygame.Surface, camera, assets: "AssetLibrary", gate_restored: bool) -> None:
        ox, oy = camera.offset()

        bg = assets.get_background(self.name, self.world_w, self.world_h)
        if bg is not None:
            screen.blit(bg, (-int(ox), -int(oy)))
        else:
            screen.fill(self.template.floor_color, (0, 0, PLAY_WIDTH, PLAY_HEIGHT))

        floor = assets.get(f"{self.name}.floor")
        x0 = max(0, int(ox // TILE_SIZE))
        x1 = min(self.width - 1, int((ox + PLAY_WIDTH) // TILE_SIZE) + 1)
        y0 = max(0, int(oy // TILE_SIZE))
        y1 = min(self.height - 1, int((oy + PLAY_HEIGHT) // TILE_SIZE) + 1)

        pulse = 0.5 + 0.5 * math.sin(self.anim * 3)

        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                ch = self.tiles[ty][tx]
                rect = pygame.Rect(tx * TILE_SIZE - int(ox), ty * TILE_SIZE - int(oy), TILE_SIZE, TILE_SIZE)
                if ch != "#" and floor is not None:
                    screen.blit(floor, rect)

                key = self._asset_key(ch, gate_restored)
                if key is not None:
                    sprite = assets.get(key)
                    if sprite is not None:
                        if ch == "R" and not self.relic_unlocked:
                            sprite = sprite.copy()
                            sprite.set_alpha(110)
                        screen.blit(sprite, rect)
                        if ch == "R" and self.relic_unlocked:
                            self._glow(screen, rect.center, self.template.relic_color, pulse)
                        continue

                self._draw_fallback(screen, rect, ch, gate_restored, pulse)

        for enemy in self.enemies:
            enemy.draw(screen, camera)
        if self.guardian:
            if self.guardian.telegraphing:
                self._draw_charge_tell(screen, camera)
            self.guardian.draw(screen, camera)
            self.guardian.draw_hp_bar(screen, camera)

    def _glow(self, screen, center, color, pulse) -> None:
        r = int(TILE_SIZE * (0.55 + 0.2 * pulse))
        glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, 70), (r, r), r)
        screen.blit(glow, (center[0] - r, center[1] - r))

    def _draw_charge_tell(self, screen, camera) -> None:
        g = self.guardian
        start = camera.apply(g.rect).center
        end = camera.apply_point(g.rect.centerx + g.charge_dir.x * 240, g.rect.centery + g.charge_dir.y * 240)
        pygame.draw.line(screen, (255, 120, 255), start, end, 3)

    def _draw_fallback(self, screen, rect, ch, gate_restored, pulse) -> None:
        if ch == "#":
            pygame.draw.rect(screen, self.template.wall_color, rect.inflate(-4, -4), border_radius=7)
        elif ch in {"1", "2", "3", "H"}:
            self._glow(screen, rect.center, self.template.portal_color, pulse)
            pygame.draw.circle(screen, self.template.portal_color, rect.center, 15)
            pygame.draw.circle(screen, (255, 255, 255), rect.center, 18, 2)
        elif ch == "R":
            color = self.template.relic_color if self.relic_unlocked else (120, 120, 140)
            if self.relic_unlocked:
                self._glow(screen, rect.center, color, pulse)
            pygame.draw.circle(screen, color, rect.center, 12)
            pygame.draw.circle(screen, (255, 255, 255), rect.center, 15, 2)
        elif ch == "G":
            col = (255, 220, 120) if gate_restored else (150, 156, 180)
            pygame.draw.rect(screen, col, rect.inflate(-8, -8), border_radius=8)
        elif ch == "W":
            col = (255, 255, 255) if gate_restored else (120, 128, 156)
            pygame.draw.ellipse(screen, col, rect.inflate(-8, -12), width=4)
        elif ch == "x":
            pygame.draw.rect(screen, (110, 120, 200), rect.inflate(-4, -4), border_radius=4)
            pygame.draw.rect(screen, (180, 195, 255), rect.inflate(-4, -4), width=2, border_radius=4)
        elif ch == "D":
            pygame.draw.rect(screen, (180, 140, 70), rect.inflate(-4, -4), border_radius=4)
            pygame.draw.circle(screen, KEY_COLOR, rect.center, 5)
        elif ch in {"s", "o"}:
            on = ch == "o"
            col = (120, 245, 160) if on else (120, 140, 180)
            pygame.draw.rect(screen, col, rect.inflate(-16, -16), border_radius=6)
            pygame.draw.rect(screen, (255, 255, 255), rect.inflate(-16, -16), width=2, border_radius=6)
        elif ch == "^":
            cx, cy = rect.center
            blink = 0.6 + 0.4 * math.sin(self.anim * 6)
            col = (int(SPIKE_COLOR[0] * blink), int(SPIKE_COLOR[1] * blink), int(SPIKE_COLOR[2] * blink))
            for dx in (-10, 0, 10):
                pygame.draw.polygon(screen, col, [
                    (cx + dx, cy - 12), (cx + dx - 5, cy + 10), (cx + dx + 5, cy + 10)])
        elif ch == "*":
            self._draw_star(screen, rect.center, STAR_COLOR, pulse)
        elif ch == "+":
            self._glow(screen, rect.center, HEAL_COLOR, pulse)
            pygame.draw.rect(screen, HEAL_COLOR, (rect.centerx - 4, rect.centery - 11, 8, 22), border_radius=2)
            pygame.draw.rect(screen, HEAL_COLOR, (rect.centerx - 11, rect.centery - 4, 22, 8), border_radius=2)
        elif ch == "K":
            self._glow(screen, rect.center, KEY_COLOR, pulse)
            pygame.draw.circle(screen, KEY_COLOR, (rect.centerx - 4, rect.centery), 7, 3)
            pygame.draw.rect(screen, KEY_COLOR, (rect.centerx + 1, rect.centery - 2, 12, 4))

    def _draw_star(self, screen, center, color, pulse) -> None:
        cx, cy = center
        r_out = 12 + 2 * pulse
        r_in = 5
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = r_out if i % 2 == 0 else r_in
            pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
        pygame.draw.polygon(screen, color, pts)
