"""Audio loading and playback for music and event sound effects."""
from __future__ import annotations

from pathlib import Path

import pygame


BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "assets" / "audio"


class AudioManager:
    def __init__(self) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music_files: dict[str, Path] = {}
        self.current_music: str | None = None
        self.current_level = "hub"
        self.music_volume = 0.45
        self.sfx_volume = 0.75
        self.music_boost = {"hub": 1.0, "selene": 3.0, "nyx": 3.0, "eos": 3.0}
        self.sound_gain = {"dash": 6.0}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
        except pygame.error:
            return

        self._load_sounds()

    def _load_sounds(self) -> None:
        files = {
            "dash": "dash.wav",
            "star": "star.wav",
            "health": "health.wav",
            "key": "key.wav",
            "switch": "switch.wav",
            "door": "door.wav",
            "hit": "hit.wav",
            "enemy_down": "enemy_down.wav",
            "guardian_hit": "guardian_hit.wav",
            "guardian_down": "guardian_down.wav",
            "relic": "relic.wav",
            "gate": "gate.wav",
            "portal": "portal.wav",
            "win": "win.wav",
        }
        for key, filename in files.items():
            path = AUDIO_DIR / filename
            if path.exists():
                self.sounds[key] = pygame.mixer.Sound(str(path))

        for level in ("hub", "selene", "nyx", "eos"):
            for ext in ("ogg", "mp3"):
                path = AUDIO_DIR / f"music_{level}.{ext}"
                if path.exists():
                    self.music_files[level] = path
                    break

    def play_music(self, level: str) -> None:
        if not self.enabled:
            return
        self.current_level = level
        path = self.music_files.get(level) or self.music_files.get("hub")
        if path is None or self.current_music == str(path):
            self._apply_music_volume()
            return
        try:
            pygame.mixer.music.fadeout(250)
            pygame.mixer.music.load(str(path))
            self._apply_music_volume()
            pygame.mixer.music.play(loops=-1)
            self.current_music = str(path)
        except pygame.error:
            self.current_music = None

    def stop_music(self) -> None:
        if self.enabled:
            pygame.mixer.music.fadeout(700)
            self.current_music = None

    def play(self, name: str, volume: float = 0.75) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        gain = self.sound_gain.get(name, 1.0)
        sound.set_volume(max(0.0, min(1.0, volume * self.sfx_volume * gain)))
        sound.play()

    def set_music_volume(self, volume: float) -> None:
        self.music_volume = max(0.0, min(1.0, volume))
        self._apply_music_volume()

    def set_sfx_volume(self, volume: float) -> None:
        self.sfx_volume = max(0.0, min(1.0, volume))

    def adjust_music_volume(self, delta: float) -> None:
        self.set_music_volume(self.music_volume + delta)

    def adjust_sfx_volume(self, delta: float) -> None:
        self.set_sfx_volume(self.sfx_volume + delta)

    def _apply_music_volume(self) -> None:
        if not self.enabled:
            return
        boosted = self.music_volume * self.music_boost.get(self.current_level, 1.0)
        pygame.mixer.music.set_volume(max(0.0, min(1.0, boosted)))
