"""Particles and floating combat/score text -- the 'juice' layer."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    radius: float
    color: tuple[int, int, int]
    gravity: float = 0.0

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= dt


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: tuple[int, int, int]
    life: float = 0.9
    max_life: float = 0.9
    vy: float = -42.0

    def update(self, dt: float) -> None:
        self.y += self.vy * dt
        self.vy *= 0.94
        self.life -= dt


class EffectSystem:
    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self._font = pygame.font.SysFont("consolas", 18, bold=True)

    # --- spawners ---
    def burst(self, x: float, y: float, color: tuple[int, int, int], count: int = 14,
              speed: float = 220.0, life: float = 0.5, gravity: float = 0.0) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            mag = random.uniform(speed * 0.3, speed)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * mag,
                vy=math.sin(angle) * mag,
                life=life * random.uniform(0.6, 1.2),
                max_life=life,
                radius=random.uniform(2, 5),
                color=color,
                gravity=gravity,
            ))

    def trail(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        self.particles.append(Particle(
            x=x, y=y,
            vx=random.uniform(-30, 30), vy=random.uniform(-30, 30),
            life=0.3, max_life=0.3, radius=random.uniform(3, 6), color=color,
        ))

    def ring(self, x: float, y: float, color: tuple[int, int, int], count: int = 18, speed: float = 260.0) -> None:
        for i in range(count):
            angle = (math.tau / count) * i
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=0.55, max_life=0.55, radius=3.5, color=color,
            ))

    def text(self, x: float, y: float, text: str, color: tuple[int, int, int]) -> None:
        self.texts.append(FloatingText(x=x, y=y, text=text, color=color))

    # --- lifecycle ---
    def update(self, dt: float) -> None:
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for t in self.texts:
            t.update(dt)
        self.texts = [t for t in self.texts if t.life > 0]

    def clear(self) -> None:
        self.particles.clear()
        self.texts.clear()

    def draw(self, screen: pygame.Surface, camera) -> None:
        for p in self.particles:
            alpha = max(0.0, min(1.0, p.life / p.max_life))
            r = max(1, int(p.radius * alpha))
            sx, sy = camera.apply_point(p.x, p.y)
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p.color, int(255 * alpha)), (r, r), r)
            screen.blit(surf, (sx - r, sy - r))

        for t in self.texts:
            alpha = max(0.0, min(1.0, t.life / t.max_life))
            label = self._font.render(t.text, True, t.color)
            label.set_alpha(int(255 * alpha))
            sx, sy = camera.apply_point(t.x, t.y)
            screen.blit(label, label.get_rect(center=(sx, sy)))
