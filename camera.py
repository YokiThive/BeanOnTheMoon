# Camera with smooth follow and screen shake
from __future__ import annotations

import random

import pygame

from settings import CAMERA_LERP, PLAY_HEIGHT, PLAY_WIDTH, SHAKE_SCALE


class Camera:
    def __init__(self, world_width: int, world_height: int) -> None:
        self.world_width = world_width
        self.world_height = world_height
        self.x = 0.0
        self.y = 0.0
        self.shake_time = 0.0
        self.shake_power = 0.0

    def resize_world(self, world_width: int, world_height: int) -> None:
        self.world_width = world_width
        self.world_height = world_height

    def _clamp(self, value: float, span: int, world: int) -> float:
        if world <= span:
            return (world - span) / 2
        return max(0.0, min(value, world - span))

    def snap_to(self, target_x: float, target_y: float) -> None:
        self.x = self._clamp(target_x - PLAY_WIDTH / 2, PLAY_WIDTH, self.world_width)
        self.y = self._clamp(target_y - PLAY_HEIGHT / 2, PLAY_HEIGHT, self.world_height)

    def tick(self, dt: float) -> None:
        if self.shake_time > 0:
            self.shake_time = max(0.0, self.shake_time - dt)

    def follow(self, target_x: float, target_y: float, dt: float) -> None:
        goal_x = self._clamp(target_x - PLAY_WIDTH / 2, PLAY_WIDTH, self.world_width)
        goal_y = self._clamp(target_y - PLAY_HEIGHT / 2, PLAY_HEIGHT, self.world_height)
        t = min(1.0, CAMERA_LERP * dt)
        self.x += (goal_x - self.x) * t
        self.y += (goal_y - self.y) * t

    def add_shake(self, power: float, duration: float = 0.3) -> None:
        self.shake_power = max(self.shake_power, power * SHAKE_SCALE)
        self.shake_time = max(self.shake_time, duration)

    def offset(self) -> tuple[float, float]:
        ox, oy = self.x, self.y
        if self.shake_time > 0:
            mag = self.shake_power * (self.shake_time / 0.3)
            ox += random.uniform(-mag, mag)
            oy += random.uniform(-mag, mag)
        return ox, oy

    def apply(self, rect: pygame.Rect | pygame.FRect) -> pygame.Rect:
        ox, oy = self.offset()
        return pygame.Rect(int(rect.x - ox), int(rect.y - oy), int(rect.width), int(rect.height))

    def apply_point(self, x: float, y: float) -> tuple[int, int]:
        ox, oy = self.offset()
        return int(x - ox), int(y - oy)
