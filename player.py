"""Bean: top-down movement plus a dash that grants i-frames and hits enemies."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from settings import (
    DASH_COOLDOWN,
    DASH_DURATION,
    DASH_IFRAMES,
    DASH_SPEED,
    PLAYER_COLOR,
    PLAYER_SIZE,
    PLAYER_SPEED,
    TILE_SIZE,
    VISOR_COLOR,
)

if TYPE_CHECKING:
    from assets import AssetLibrary
    from level import Level


class Player:
    def __init__(self) -> None:
        self.rect = pygame.FRect(72, 72, PLAYER_SIZE, PLAYER_SIZE)
        self.facing = pygame.Vector2(0, 1)
        self.dash_time = 0.0
        self.dash_cd = 0.0
        self.invuln = 0.0
        self.dash_dir = pygame.Vector2(0, 1)
        self.moving = False

    # --- positioning ---
    def spawn_at(self, tile_x: int, tile_y: int) -> None:
        self.rect.center = (
            tile_x * TILE_SIZE + TILE_SIZE / 2,
            tile_y * TILE_SIZE + TILE_SIZE / 2,
        )
        self.dash_time = 0.0
        self.invuln = max(self.invuln, 0.6)  # brief grace on (re)spawn

    @property
    def center(self) -> tuple[float, float]:
        return self.rect.centerx, self.rect.centery

    @property
    def is_dashing(self) -> bool:
        return self.dash_time > 0

    @property
    def invulnerable(self) -> bool:
        return self.invuln > 0

    def can_dash(self) -> bool:
        return self.dash_cd <= 0 and self.dash_time <= 0

    def start_dash(self) -> bool:
        if not self.can_dash():
            return False
        self.dash_dir = pygame.Vector2(self.facing)
        if self.dash_dir.length_squared() == 0:
            self.dash_dir = pygame.Vector2(0, 1)
        self.dash_dir = self.dash_dir.normalize()
        self.dash_time = DASH_DURATION
        self.dash_cd = DASH_COOLDOWN
        self.invuln = max(self.invuln, DASH_IFRAMES)
        return True

    def hurt_grace(self, seconds: float) -> None:
        self.invuln = max(self.invuln, seconds)

    # --- per-frame ---
    def _move(self, dx: float, dy: float, level: "Level") -> None:
        if dx:
            self.rect.x += dx
            if self._hits_wall(level):
                self.rect.x -= dx
        if dy:
            self.rect.y += dy
            if self._hits_wall(level):
                self.rect.y -= dy

    def _hits_wall(self, level: "Level") -> bool:
        r = self.rect
        pts = [
            (r.left + 3, r.top + 3),
            (r.right - 3, r.top + 3),
            (r.left + 3, r.bottom - 3),
            (r.right - 3, r.bottom - 3),
        ]
        return any(level.is_wall_at_pixel(px, py) for px, py in pts)

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper, level: "Level") -> None:
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.invuln = max(0.0, self.invuln - dt)

        if self.dash_time > 0:
            self.dash_time = max(0.0, self.dash_time - dt)
            self._move(self.dash_dir.x * DASH_SPEED * dt, self.dash_dir.y * DASH_SPEED * dt, level)
            self.moving = True
            return

        mx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        my = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        self.moving = mx != 0 or my != 0

        if self.moving:
            vec = pygame.Vector2(mx, my)
            if vec.length_squared() > 0:
                self.facing = vec.normalize()
                vec = self.facing * PLAYER_SPEED
                self._move(vec.x * dt, vec.y * dt, level)

    # --- render ---
    def draw(self, screen: pygame.Surface, camera, assets: "AssetLibrary") -> None:
        r = camera.apply(self.rect)

        if self.invuln > 0 and not self.is_dashing and int(self.invuln * 20) % 2 == 0:
            return

        if self.is_dashing:
            glow = pygame.Surface((r.width + 16, r.height + 16), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (150, 240, 255, 120), glow.get_rect())
            screen.blit(glow, (r.centerx - glow.get_width() // 2, r.centery - glow.get_height() // 2))

        sprite = assets.get("player.bean")
        if sprite is not None:
            screen.blit(sprite, r)
        else:
            pygame.draw.ellipse(screen, PLAYER_COLOR, r)
            visor = pygame.Rect(r.x + 8, r.y + 6, 14, 9)
            pygame.draw.ellipse(screen, VISOR_COLOR, visor)
