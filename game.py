"""Bean on the Moon -- main game loop, states, HUD and juice integration."""
from __future__ import annotations

import time

import pygame

from assets import AssetLibrary
from audio import AudioManager
from camera import Camera
from data import LEVEL_TEMPLATES, PORTAL_DESTINATIONS
from effects import EffectSystem
from level import Level
from player import Player
from settings import (
    BG_COLOR,
    DAMAGE_COOLDOWN,
    DASH_COLOR,
    DASH_COOLDOWN,
    FPS,
    HEART_EMPTY,
    HEART_FULL,
    MAX_HEALTH,
    PLAY_HEIGHT,
    STAR_COLOR,
    TEXT_DIM,
    TEXT_GOLD,
    TEXT_MAIN,
    TILE_SIZE,
    UI_BG,
    UI_HEIGHT,
    UI_LINE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)

TOTAL_STARS = sum(row.count("*") for t in LEVEL_TEMPLATES.values() for row in t.layout)
WINDOW_FLAGS = pygame.SCALED | pygame.RESIZABLE


class Game:
    def __init__(self) -> None:
        pygame.init()
        # SCALED keeps the logical resolution at 960x640 while letting the OS
        # scale the resizable window and fullscreen while preserving game aspect.
        self.fullscreen = False
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), WINDOW_FLAGS)
        pygame.display.set_caption("Bean on the Moon")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)
        self.small = pygame.font.SysFont("consolas", 18)
        self.big = pygame.font.SysFont("consolas", 40, bold=True)
        self.mid = pygame.font.SysFont("consolas", 26, bold=True)

        self.assets = AssetLibrary()
        self.audio = AudioManager()
        self.effects = EffectSystem()
        self.player = Player()
        self.camera = Camera(WINDOW_WIDTH, PLAY_HEIGHT)

        self.collected_relics: set[str] = set()
        self.level_states: dict[str, dict] = {name: {} for name in LEVEL_TEMPLATES}
        self.gate_restored = False
        self.stars = 0

        self.state = "title"      # title | play | pause | win
        self.health = MAX_HEALTH
        self.hit_flash = 0.0
        self.message = ""
        self.banner = ""
        self.banner_time = 0.0
        self.pause_buttons: dict[str, pygame.Rect] = {}
        self.start_time = time.perf_counter()
        self.win_time: float | None = None
        self.current_level: Level | None = None

        self.load_level("hub")

    # ---------- level management ----------
    def load_level(self, name: str) -> None:
        self.current_level = Level(name, LEVEL_TEMPLATES[name], self.level_states[name], name in self.collected_relics)
        self.camera.resize_world(self.current_level.world_w, self.current_level.world_h)
        sx, sy = self.current_level.spawn_tile()
        self.player.spawn_at(sx, sy)
        self.camera.snap_to(*self.player.center)
        self.effects.clear()
        self.set_banner(self.current_level.title, LEVEL_TEMPLATES[name].intro)
        self.message = LEVEL_TEMPLATES[name].intro
        self.audio.play_music(name)

    def respawn(self) -> None:
        self.health = MAX_HEALTH
        name = self.current_level.name
        self.load_level(name)
        self.message = "Bean's suit reboots at the landing zone. Progress kept."

    def set_banner(self, title: str, subtitle: str) -> None:
        self.banner = title
        self.banner_sub = subtitle
        self.banner_time = 2.4

    # ---------- main loop ----------
    def run(self) -> None:
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self.on_keydown(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    running = self.on_mouse_down(event.pos)
                elif event.type in (pygame.VIDEORESIZE, pygame.WINDOWRESIZED):
                    self.on_resize(event)
            self.update(dt)
            self.draw()
        pygame.quit()

    def toggle_fullscreen(self) -> None:
        try:
            pygame.display.toggle_fullscreen()
            self.fullscreen = not self.fullscreen
        except pygame.error:
            pass  # some drivers/platforms don't support runtime toggling

    def on_resize(self, event: pygame.event.Event) -> None:
        # pygame.SCALED keeps the 960x640 game surface aspect-correct inside
        # whatever window/fullscreen size the OS provides. Forcing the native
        # window size here causes snap-back on manual resize and top-bar fullscreen.
        return

    def on_keydown(self, key: int) -> bool:
        if key in (pygame.K_F11, pygame.K_f):
            self.toggle_fullscreen()
            return True
        if key == pygame.K_ESCAPE:
            if self.fullscreen:
                self.toggle_fullscreen()
                return True
            if self.state == "play":
                self.state = "pause"
                return True
            if self.state == "pause":
                self.state = "play"
                return True
            return False
        if self.state == "title":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = "play"
                self.start_time = time.perf_counter()
                self.message = "Reach a portal and press E to dive into a moon."
            return True
        if self.state == "win":
            return True
        if self.state == "pause":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = "play"
            elif key in (pygame.K_q, pygame.K_BACKSPACE):
                return False
            elif key in (pygame.K_LEFT, pygame.K_MINUS):
                self.audio.adjust_music_volume(-0.05)
            elif key in (pygame.K_RIGHT, pygame.K_EQUALS, pygame.K_PLUS):
                self.audio.adjust_music_volume(0.05)
            elif key == pygame.K_a:
                self.audio.adjust_sfx_volume(-0.05)
                self.audio.play("star", 0.7)
            elif key == pygame.K_s:
                self.audio.adjust_sfx_volume(0.05)
                self.audio.play("star", 0.7)
            return True
        if key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_j):
            if self.player.start_dash():
                self.effects.burst(*self.player.center, DASH_COLOR, count=8, speed=120, life=0.3)
                self.audio.play("dash")
        if key == pygame.K_e:
            self.try_interact()
        return True

    def on_mouse_down(self, pos: tuple[int, int]) -> bool:
        if self.state != "pause":
            return True
        for name, rect in self.pause_buttons.items():
            if not rect.collidepoint(pos):
                continue
            if name == "resume":
                self.state = "play"
            elif name == "quit":
                return False
            elif name == "music_down":
                self.audio.adjust_music_volume(-0.05)
            elif name == "music_up":
                self.audio.adjust_music_volume(0.05)
            elif name == "sfx_down":
                self.audio.adjust_sfx_volume(-0.05)
                self.audio.play("star", 0.7)
            elif name == "sfx_up":
                self.audio.adjust_sfx_volume(0.05)
                self.audio.play("star", 0.7)
            return True
        return True

    # ---------- update ----------
    def update(self, dt: float) -> None:
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.banner_time = max(0.0, self.banner_time - dt)
        self.effects.update(dt)
        self.camera.tick(dt)

        if self.state != "play":
            return

        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.current_level)

        if self.player.is_dashing:
            self.effects.trail(*self.player.center, DASH_COLOR)

        result = self.current_level.update(dt, self.player, self.effects)
        self.handle_result(result)

        self.camera.follow(*self.player.center, dt)

    def handle_result(self, result: dict) -> None:
        if result["stars"]:
            self.stars += result["stars"]
            self.effects.text(*self.player.center, "+1 star", STAR_COLOR)
            self.audio.play("star")
        if result["health"]:
            self.health = min(MAX_HEALTH, self.health + 1)
            self.effects.text(*self.player.center, "+1 HP", (140, 245, 160))
            self.message = "Suit repaired. +1 integrity."
            self.audio.play("health")
        if result["key"]:
            self.message = "Picked up a key."
            self.effects.text(*self.player.center, "Key", (255, 220, 110))
            self.audio.play("key")
        if result["door"]:
            self.message = "The locked door swings open."
            self.audio.play("door")
        if result["switch"] == "partial":
            self.message = "Switch online. Find the other one to drop the seal."
            self.audio.play("switch")
        elif result["switch"] == "opened":
            self.message = "Both switches active -- the guardian's seal collapses!"
            self.camera.add_shake(5, 0.3)
            self.audio.play("switch", 0.9)
        if result["enemy_killed"]:
            self.camera.add_shake(4, 0.2)
            self.audio.play("enemy_down")
        if result["guardian_hit"]:
            self.camera.add_shake(5, 0.25)
            self.audio.play("guardian_hit")
        if result["guardian_killed"]:
            self.camera.add_shake(12, 0.5)
            self.message = f"The {self.current_level.title} guardian is destroyed! The relic is yours to take."
            self.effects.text(*self.player.center, "GUARDIAN DOWN", (255, 200, 255))
            self.audio.play("guardian_down", 0.9)
        if result["damage"]:
            self.hit_player(result["damage"])

    def hit_player(self, message: str) -> None:
        if self.player.invulnerable:
            return
        self.health -= 1
        self.player.hurt_grace(DAMAGE_COOLDOWN)
        self.hit_flash = 0.25
        self.camera.add_shake(8, 0.3)
        self.effects.burst(*self.player.center, (255, 120, 130), count=14, speed=200)
        self.audio.play("hit")
        if self.health <= 0:
            self.respawn()
        else:
            self.message = f"{message}  ({self.health}/{MAX_HEALTH})"

    def try_interact(self) -> None:
        if self.state != "play":
            return
        interaction = self.current_level.interaction_near(self.player)
        if interaction is None:
            return
        ch, tx, ty = interaction
        name = self.current_level.name

        if ch in PORTAL_DESTINATIONS and name == "hub":
            self.audio.play("portal")
            self.load_level(PORTAL_DESTINATIONS[ch])
            return
        if ch == "H":
            self.audio.play("portal")
            self.load_level("hub")
            return
        if ch == "R":
            if name in self.collected_relics:
                return
            if not self.current_level.relic_unlocked:
                self.message = "The relic is sealed. Defeat the moon's guardian first."
                return
            self.collected_relics.add(name)
            self.current_level._replace("R", ".")
            self.effects.ring(self.player.center[0], self.player.center[1], self.current_level.template.relic_color, count=26, speed=300)
            self.effects.text(*self.player.center, f"{self.current_level.title} relic!", TEXT_GOLD)
            self.camera.add_shake(6, 0.4)
            self.audio.play("relic", 0.9)
            got = len(self.collected_relics)
            if got >= 3:
                self.message = "All three relics gathered! Return to the hub and restore the Lunar Gate."
            else:
                self.message = f"Relic recovered ({got}/3). Head back through the portal."
            return
        if ch == "G":
            if len(self.collected_relics) < 3:
                self.message = f"The Lunar Gate needs all 3 relics ({len(self.collected_relics)}/3)."
                return
            if not self.gate_restored:
                self.gate_restored = True
                self.message = "The Lunar Gate roars to life. The Warp Gate is now active!"
                self.effects.ring(*self.player.center, (255, 226, 138), count=30, speed=320)
                self.camera.add_shake(10, 0.5)
                self.audio.play("gate", 0.9)
            else:
                self.message = "The Lunar Gate is already restored."
            return
        if ch == "W":
            if not self.gate_restored:
                self.message = "The Warp Gate is dormant. Restore the Lunar Gate first."
                return
            self.state = "win"
            self.win_time = time.perf_counter()
            self.message = "The Warp Gate opens. Bean steps through, and goes home."
            self.effects.ring(*self.player.center, (255, 255, 255), count=40, speed=360)
            self.camera.add_shake(14, 0.6)
            self.audio.stop_music()
            self.audio.play("win", 0.9)

    # ---------- objective / hint text ----------
    def objective_text(self) -> str:
        lvl = self.current_level
        name = lvl.name
        if name == "hub":
            if len(self.collected_relics) < 3:
                return f"Explore the moons and recover all relics ({len(self.collected_relics)}/3)"
            if not self.gate_restored:
                return "Restore the Lunar Gate (press E)"
            return "Enter the Warp Gate to go home"
        if name in self.collected_relics:
            return "Relic secured. Return through the hub portal."
        if not lvl.state.get("barriers_open") and lvl.total_switches:
            done = len(lvl.state.get("switches", set()))
            return f"Find the switches to unseal the guardian ({done}/{lvl.total_switches})"
        if not lvl.relic_unlocked:
            return "Defeat the guardian (dash into it!)"
        return "Grab the relic (press E)"

    def hint_text(self) -> str | None:
        interaction = self.current_level.interaction_near(self.player)
        if interaction is None:
            return None
        ch, _, _ = interaction
        if ch in PORTAL_DESTINATIONS and self.current_level.name == "hub":
            return f"Press E to enter {LEVEL_TEMPLATES[PORTAL_DESTINATIONS[ch]].title}"
        if ch == "H":
            return "Press E to return to the hub"
        if ch == "R":
            return "Press E to take the relic" if self.current_level.relic_unlocked else "Sealed -- defeat the guardian"
        if ch == "G":
            if len(self.collected_relics) < 3:
                return "Needs all 3 relics"
            return "Press E to restore the Lunar Gate" if not self.gate_restored else "Already restored"
        if ch == "W":
            return "Press E to warp home" if self.gate_restored else "Dormant -- restore the Lunar Gate"
        return None

    # ---------- drawing ----------
    def draw(self) -> None:
        self.screen.fill(BG_COLOR)
        play_area = self.screen.subsurface((0, 0, WINDOW_WIDTH, PLAY_HEIGHT))
        self.current_level.draw(play_area, self.camera, self.assets, self.gate_restored)
        self.player.draw(play_area, self.camera, self.assets)
        self.effects.draw(play_area, self.camera)

        if self.hit_flash > 0:
            tint = pygame.Surface((WINDOW_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
            tint.fill((255, 40, 60, int(120 * (self.hit_flash / 0.25))))
            play_area.blit(tint, (0, 0))

        self.draw_hud()

        if self.banner_time > 0 and self.state == "play":
            self.draw_banner()
        if self.state == "title":
            self.draw_title()
        if self.state == "pause":
            self.draw_pause()
        if self.state == "win":
            self.draw_win()
        pygame.display.flip()

    def draw_hud(self) -> None:
        rect = pygame.Rect(0, WINDOW_HEIGHT - UI_HEIGHT, WINDOW_WIDTH, UI_HEIGHT)
        pygame.draw.rect(self.screen, UI_BG, rect)
        pygame.draw.line(self.screen, UI_LINE, rect.topleft, rect.topright, 2)
        y0 = WINDOW_HEIGHT - UI_HEIGHT + 8
        row2 = y0 + 30
        row3 = y0 + 56

        # Row 1: hearts, relics, stars, dash bar, location
        for i in range(MAX_HEALTH):
            cx = 22 + i * 26
            color = HEART_FULL if i < self.health else HEART_EMPTY
            self._draw_heart(cx, y0 + 7, color)

        relics = self.small.render(f"Relics {len(self.collected_relics)}/3", True, TEXT_MAIN)
        stars = self.small.render(f"Stars {self.stars}/{TOTAL_STARS}", True, STAR_COLOR)
        self.screen.blit(relics, (172, y0))
        self.screen.blit(stars, (300, y0))

        ready = self.player.dash_cd <= 0
        label = self.small.render("DASH", True, TEXT_MAIN if ready else TEXT_DIM)
        self.screen.blit(label, (430, y0))
        bar = pygame.Rect(492, y0 + 2, 90, 14)
        pygame.draw.rect(self.screen, (40, 46, 70), bar, border_radius=4)
        frac = 1.0 if ready else 1.0 - (self.player.dash_cd / DASH_COOLDOWN)
        fill = (120, 240, 255) if ready else (90, 130, 160)
        pygame.draw.rect(self.screen, fill, (bar.x, bar.y, int(bar.width * frac), bar.height), border_radius=4)

        loc = self.small.render(self.current_level.title, True, TEXT_DIM)
        self.screen.blit(loc, (WINDOW_WIDTH - loc.get_width() - 16, y0))

        # Row 2: current objective
        obj = self.font.render(self.objective_text(), True, TEXT_GOLD)
        self.screen.blit(obj, (22, row2))

        # Row 3: controls reference
        ctrl = self.small.render("WASD move   E interact   Shift / Space dash   Esc pause   F fullscreen", True, TEXT_DIM)
        self.screen.blit(ctrl, (22, row3))

        # floating message just above the HUD
        if self.message:
            msg = self.small.render(self.message, True, (255, 244, 200))
            mrect = msg.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - UI_HEIGHT - 16))
            pygame.draw.rect(self.screen, (16, 20, 34), mrect.inflate(20, 10), border_radius=8)
            self.screen.blit(msg, mrect)

        hint = self.hint_text()
        if hint and self.state == "play":
            h = self.small.render(hint, True, TEXT_MAIN)
            hrect = h.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - UI_HEIGHT - 46))
            pygame.draw.rect(self.screen, (24, 30, 50), hrect.inflate(20, 10), border_radius=8)
            self.screen.blit(h, hrect)

    def _draw_heart(self, x: int, y: int, color) -> None:
        pygame.draw.circle(self.screen, color, (x - 5, y), 6)
        pygame.draw.circle(self.screen, color, (x + 5, y), 6)
        pygame.draw.polygon(self.screen, color, [(x - 10, y + 2), (x + 10, y + 2), (x, y + 14)])

    def draw_banner(self) -> None:
        alpha = min(1.0, self.banner_time / 0.6)
        title = self.mid.render(self.banner, True, TEXT_MAIN)
        sub = self.small.render(getattr(self, "banner_sub", ""), True, TEXT_DIM)
        surf = pygame.Surface((max(title.get_width(), sub.get_width()) + 50, 78), pygame.SRCALPHA)
        surf.fill((10, 12, 24, int(180 * alpha)))
        surf.blit(title, title.get_rect(center=(surf.get_width() // 2, 26)))
        surf.blit(sub, sub.get_rect(center=(surf.get_width() // 2, 56)))
        surf.set_alpha(int(255 * alpha))
        self.screen.blit(surf, surf.get_rect(center=(WINDOW_WIDTH // 2, 70)))

    def draw_pause(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 7, 18, 215))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(0, 0, 470, 390)
        panel.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        pygame.draw.rect(self.screen, (18, 23, 42), panel, border_radius=18)
        pygame.draw.rect(self.screen, UI_LINE, panel, width=2, border_radius=18)

        title = self.big.render("PAUSED", True, TEXT_MAIN)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 54)))

        self.pause_buttons = {}
        music_pct = int(self.audio.music_volume * 100)
        sfx_pct = int(self.audio.sfx_volume * 100)
        self._draw_volume_row(panel.y + 115, "Music", music_pct, "music_down", "music_up")
        self._draw_volume_row(panel.y + 175, "SFX", sfx_pct, "sfx_down", "sfx_up")

        resume = pygame.Rect(panel.centerx - 145, panel.y + 250, 130, 46)
        quit_btn = pygame.Rect(panel.centerx + 15, panel.y + 250, 130, 46)
        self.pause_buttons["resume"] = resume
        self.pause_buttons["quit"] = quit_btn
        self._draw_button(resume, "Resume")
        self._draw_button(quit_btn, "Quit")

        hint = self.small.render("Esc/Enter resume   Left/Right music   A/S SFX   Q quit", True, TEXT_DIM)
        self.screen.blit(hint, hint.get_rect(center=(panel.centerx, panel.bottom - 42)))

    def _draw_volume_row(self, y: int, label: str, pct: int, down_name: str, up_name: str) -> None:
        label_surf = self.font.render(label, True, TEXT_MAIN)
        self.screen.blit(label_surf, (WINDOW_WIDTH // 2 - 170, y + 9))
        down = pygame.Rect(WINDOW_WIDTH // 2 - 45, y, 42, 42)
        up = pygame.Rect(WINDOW_WIDTH // 2 + 125, y, 42, 42)
        self.pause_buttons[down_name] = down
        self.pause_buttons[up_name] = up
        self._draw_button(down, "-")
        self._draw_button(up, "+")
        value = self.font.render(f"{pct:3d}%", True, TEXT_GOLD)
        self.screen.blit(value, value.get_rect(center=(WINDOW_WIDTH // 2 + 62, y + 21)))

    def _draw_button(self, rect: pygame.Rect, text: str) -> None:
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint((mx, my))
        color = (44, 55, 88) if hover else (31, 39, 68)
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, UI_LINE, rect, width=2, border_radius=10)
        label = self.font.render(text, True, TEXT_MAIN)
        self.screen.blit(label, label.get_rect(center=rect.center))

    def draw_title(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 220))
        self.screen.blit(overlay, (0, 0))
        title = self.big.render("BEAN ON THE MOON", True, TEXT_MAIN)
        self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 96)))
        lines = [
            "Bean was yanked through a portal onto an ancient planet.",
            "Three moons each hide a relic behind a guardian.",
            "",
            "Move: WASD / Arrows      Interact: E",
            "DASH: Shift or Space -- dodge danger AND smash enemies.",
            "Dash THROUGH a guardian to damage it. Touch one and you get hurt.",
            "",
            "Collect 3 relics, restore the Lunar Gate, open the Warp Gate.",
            "",
            "Esc pauses during play. F or F11 toggles fullscreen.",
        ]
        for i, line in enumerate(lines):
            color = TEXT_GOLD if "DASH" in line else TEXT_DIM
            t = self.small.render(line, True, color)
            self.screen.blit(t, t.get_rect(center=(WINDOW_WIDTH // 2, 170 + i * 30)))
        prompt = self.font.render("Press Enter to begin", True, TEXT_MAIN)
        self.screen.blit(prompt, prompt.get_rect(center=(WINDOW_WIDTH // 2, 470)))

    def draw_win(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 210))
        self.screen.blit(overlay, (0, 0))
        title = self.big.render("BEAN MADE IT HOME", True, TEXT_MAIN)
        self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 200)))
        end = self.win_time if self.win_time is not None else time.perf_counter()
        elapsed = int(end - self.start_time)
        stats = [
            f"Time: {elapsed // 60:02}:{elapsed % 60:02}",
            f"Relics: {len(self.collected_relics)}/3",
            f"Stars: {self.stars}/{TOTAL_STARS}",
        ]
        for i, s in enumerate(stats):
            t = self.font.render(s, True, TEXT_GOLD)
            self.screen.blit(t, t.get_rect(center=(WINDOW_WIDTH // 2, 270 + i * 36)))
        prompt = self.small.render("Press Esc to quit", True, TEXT_DIM)
        self.screen.blit(prompt, prompt.get_rect(center=(WINDOW_WIDTH // 2, 420)))
