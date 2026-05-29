"""Enemies: chasers, patrollers, and moon guardians (mini-bosses).

Combat verb: Bean's dash deals contact damage and is invulnerable.
Touching an enemy while NOT dashing hurts Bean instead.
"""
from __future__ import annotations

import math
import random

import pygame

from settings import (
    CHASER_AGGRO,
    CHASER_HP,
    CHASER_SPEED,
    ENEMY_COLOR,
    ENEMY_CORE,
    ENEMY_HIT_COOLDOWN,
    GUARDIAN_CHARGE_SPEED,
    GUARDIAN_COLOR,
    GUARDIAN_CORE,
    GUARDIAN_HP,
    GUARDIAN_SPEED,
    PATROLLER_HP,
    PATROLLER_SPEED,
    TILE_SIZE,
)


def _move_axis(rect: pygame.FRect, dx: float, dy: float, level) -> bool:
    """Move on one axis; revert and report a wall hit if it collides."""
    rect.x += dx
    rect.y += dy
    pts = [
        (rect.left + 3, rect.top + 3),
        (rect.right - 3, rect.top + 3),
        (rect.left + 3, rect.bottom - 3),
        (rect.right - 3, rect.bottom - 3),
    ]
    if any(level.is_wall_at_pixel(px, py) for px, py in pts):
        rect.x -= dx
        rect.y -= dy
        return True
    return False


class Enemy:
    kind = "enemy"

    def __init__(self, x: float, y: float, size: int = 36) -> None:
        self.rect = pygame.FRect(x, y, size, size)
        self.hp = 1
        self.max_hp = 1
        self.alive = True
        self.hit_cd = 0.0
        self.flash = 0.0
        self.anim = random.uniform(0, math.tau)
        self.color = ENEMY_COLOR
        self.core = ENEMY_CORE

    @property
    def center(self) -> tuple[float, float]:
        return self.rect.centerx, self.rect.centery

    def take_hit(self, damage: int = 1) -> bool:
        """Return True if this hit killed the enemy."""
        if self.hit_cd > 0:
            return False
        self.hp -= damage
        self.hit_cd = ENEMY_HIT_COOLDOWN
        self.flash = 0.18
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def _tick_timers(self, dt: float) -> None:
        self.hit_cd = max(0.0, self.hit_cd - dt)
        self.flash = max(0.0, self.flash - dt)
        self.anim += dt

    def update(self, dt: float, player_center: tuple[float, float], level) -> None:  # noqa: ARG002
        self._tick_timers(dt)

    def _draw_body(self, screen, camera, radius_pad: int = 0) -> None:
        r = camera.apply(self.rect)
        col = (255, 255, 255) if self.flash > 0 else self.color
        pulse = 2 + int(2 * math.sin(self.anim * 6))
        pygame.draw.circle(screen, col, r.center, r.width // 2 + radius_pad + pulse)
        pygame.draw.circle(screen, self.core, r.center, max(3, r.width // 4))

    def draw(self, screen, camera) -> None:
        self._draw_body(screen, camera)

    def draw_hp_bar(self, screen, camera) -> None:
        pass


class Chaser(Enemy):
    kind = "chaser"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, size=34)
        self.hp = self.max_hp = CHASER_HP
        self.wander = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        self.retarget = 0.0

    def update(self, dt: float, player_center, level) -> None:
        self._tick_timers(dt)
        px, py = player_center
        dx = px - self.rect.centerx
        dy = py - self.rect.centery
        dist = math.hypot(dx, dy)

        if dist < CHASER_AGGRO and dist > 1:
            vx = dx / dist * CHASER_SPEED
            vy = dy / dist * CHASER_SPEED
        else:
            self.retarget -= dt
            if self.retarget <= 0:
                self.wander = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
                self.retarget = random.uniform(0.8, 1.8)
            vx = self.wander.x * CHASER_SPEED * 0.45
            vy = self.wander.y * CHASER_SPEED * 0.45

        if _move_axis(self.rect, vx * dt, 0, level):
            self.wander.x *= -1
        if _move_axis(self.rect, 0, vy * dt, level):
            self.wander.y *= -1


class Patroller(Enemy):
    kind = "patroller"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, size=36)
        self.hp = self.max_hp = PATROLLER_HP
        self.color = (236, 140, 92)
        self.core = (255, 214, 170)
        angle = random.choice([0, math.pi / 2, math.pi, 3 * math.pi / 2])
        self.dir = pygame.Vector2(math.cos(angle), math.sin(angle))

    def update(self, dt: float, player_center, level) -> None:
        self._tick_timers(dt)
        speed = PATROLLER_SPEED
        # Slight nudge toward player when close, otherwise straight patrol.
        px, py = player_center
        if math.hypot(px - self.rect.centerx, py - self.rect.centery) < 170:
            speed *= 1.4

        if _move_axis(self.rect, self.dir.x * speed * dt, 0, level):
            self.dir.x *= -1
        if _move_axis(self.rect, 0, self.dir.y * speed * dt, level):
            self.dir.y *= -1

    def draw(self, screen, camera) -> None:
        r = camera.apply(self.rect)
        col = (255, 255, 255) if self.flash > 0 else self.color
        pts = [
            (r.centerx, r.top),
            (r.right, r.centery),
            (r.centerx, r.bottom),
            (r.left, r.centery),
        ]
        pygame.draw.polygon(screen, col, pts)
        pygame.draw.circle(screen, self.core, r.center, max(3, r.width // 5))


class Guardian(Enemy):
    kind = "guardian"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, size=64)
        self.hp = self.max_hp = GUARDIAN_HP
        self.color = GUARDIAN_COLOR
        self.core = GUARDIAN_CORE
        self.state = "chase"
        self.state_time = random.uniform(1.5, 2.5)
        self.charge_dir = pygame.Vector2()

    def update(self, dt: float, player_center, level) -> None:
        self._tick_timers(dt)
        px, py = player_center
        self.state_time -= dt

        if self.state == "chase":
            dx, dy = px - self.rect.centerx, py - self.rect.centery
            dist = math.hypot(dx, dy) or 1
            vx, vy = dx / dist * GUARDIAN_SPEED, dy / dist * GUARDIAN_SPEED
            _move_axis(self.rect, vx * dt, 0, level)
            _move_axis(self.rect, 0, vy * dt, level)
            if self.state_time <= 0:
                self.state = "telegraph"
                self.state_time = 0.7

        elif self.state == "telegraph":
            # Lock onto the player, then charge.
            dx, dy = px - self.rect.centerx, py - self.rect.centery
            dist = math.hypot(dx, dy) or 1
            self.charge_dir = pygame.Vector2(dx / dist, dy / dist)
            if self.state_time <= 0:
                self.state = "charge"
                self.state_time = 0.55

        elif self.state == "charge":
            vx = self.charge_dir.x * GUARDIAN_CHARGE_SPEED
            vy = self.charge_dir.y * GUARDIAN_CHARGE_SPEED
            hit_x = _move_axis(self.rect, vx * dt, 0, level)
            hit_y = _move_axis(self.rect, 0, vy * dt, level)
            if self.state_time <= 0 or hit_x or hit_y:
                self.state = "recover"
                self.state_time = 0.6

        else:  # recover -- vulnerable window, stands still
            if self.state_time <= 0:
                self.state = "chase"
                self.state_time = random.uniform(1.6, 2.6)

    @property
    def telegraphing(self) -> bool:
        return self.state == "telegraph"

    def draw(self, screen, camera) -> None:
        r = camera.apply(self.rect)
        if self.flash > 0:
            col = (255, 255, 255)
        elif self.state == "telegraph":
            # Pulse bright as a wind-up tell.
            t = 0.5 + 0.5 * math.sin(self.anim * 26)
            col = (int(220 + 35 * t), int(120 + 80 * t), 255)
        elif self.state == "recover":
            col = (120, 70, 150)
        else:
            col = self.color
        pulse = 3 + int(3 * math.sin(self.anim * 4))
        pygame.draw.circle(screen, col, r.center, r.width // 2 + pulse)
        pygame.draw.circle(screen, (30, 10, 50), r.center, r.width // 2 - 4, 3)
        pygame.draw.circle(screen, self.core, r.center, r.width // 4)
        if self.state == "charge":
            pygame.draw.circle(screen, (255, 255, 255), r.center, r.width // 2 + pulse, 3)

    def draw_hp_bar(self, screen, camera) -> None:
        r = camera.apply(self.rect)
        w = 70
        x = r.centerx - w // 2
        y = r.top - 14
        pygame.draw.rect(screen, (40, 20, 40), (x, y, w, 7), border_radius=3)
        frac = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(screen, (235, 90, 235), (x, y, int(w * frac), 7), border_radius=3)


def make_enemy(kind: str, tile_x: int, tile_y: int) -> Enemy:
    cx = tile_x * TILE_SIZE + TILE_SIZE / 2
    cy = tile_y * TILE_SIZE + TILE_SIZE / 2
    if kind == "chaser":
        e = Chaser(0, 0)
    elif kind == "patroller":
        e = Patroller(0, 0)
    elif kind == "guardian":
        e = Guardian(0, 0)
    else:
        e = Chaser(0, 0)
    e.rect.center = (cx, cy)
    return e
