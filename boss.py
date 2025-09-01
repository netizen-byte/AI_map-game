"""Boss entity implementation.

The boss chases the player but only inflicts damage during the attack animation's
designated hit frame (no passive touch damage while walking). This keeps combat
fair and telegraphed.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import pygame

from constants import TILE
try:
    from constants import BOSS_ATTACK_DAMAGE
except Exception:  # fallback if constant missing
    BOSS_ATTACK_DAMAGE = 2
try:
    from constants import ANIM_FPS
except Exception:
    ANIM_FPS = 8


def _load_strip(folder: Path, out_wh: Tuple[int, int]) -> List[pygame.Surface]:
    frames: List[pygame.Surface] = []
    if not folder.exists():
        return frames
    for p in sorted(folder.iterdir(), key=lambda q: q.name):
        if p.suffix.lower() not in (".png", ".webp"):
            continue
        try:
            img = pygame.image.load(p.as_posix()).convert_alpha()
            frames.append(pygame.transform.scale(img, out_wh))
        except Exception:
            pass
    return frames


class Boss:
    """Raccoon boss that pursues the player and only deals damage on attack hit frame."""

    def __init__(self, pos: Tuple[int, int], tile_size: int = TILE):
        self.size_tiles = 2
        self.w = self.h = self.size_tiles * tile_size
        self.offset_y = -int(0.25 * tile_size)

        base = Path("monsters") / "raccoon"
        self.anim: Dict[str, List[pygame.Surface]] = {
            "idle": _load_strip(base / "idle", (self.w, self.h)),
            "move": _load_strip(base / "move", (self.w, self.h)),
            "attack": _load_strip(base / "attack", (self.w, self.h)),
        }
        if not self.anim["idle"]:  # fallback dummy
            dummy = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            pygame.draw.circle(dummy, (240, 180, 50, 220), (self.w // 2, self.h // 2), self.w // 2)
            self.anim["idle"] = [dummy]
            self.anim["move"] = [dummy]
            self.anim["attack"] = [dummy]

        # animation state
        self.state = "idle"
        self.frame = 0
        self.timer = 0.0

        # positioning / collision
        self.pos = pygame.Vector2(pos)
        self.rect = pygame.Rect(0, 0, self.w, self.h)
        self.rect.midbottom = (int(self.pos.x), int(self.pos.y) + self.offset_y)
        self.hitbox = self.rect.inflate(-self.w // 4, -self.h // 4)

        # stats
        self.max_hp = 20
        self.hp = self.max_hp
        self.speed = 90.0
        self.notice_radius = 3 * tile_size
        self.attack_radius = 1 * tile_size

        # attack logic
        self.attack_damage = BOSS_ATTACK_DAMAGE
        self.attack_cooldown = 0.8  # seconds between attack starts
        self._attack_cd = 0.0
        atk_frames = self.anim.get("attack", []) or [None]
        self.attack_hit_frame = max(0, (len(atk_frames) // 2) - 1) if len(atk_frames) > 2 else 0
        self._did_hit_this_attack = False
        self.attack_anim_length = max(0.5, (len(atk_frames) / ANIM_FPS) if len(atk_frames) > 1 else 0.5)
        self._attack_time = 0.0

        self.alive = True

    # ------------------------------------------------------------------
    def _set_state(self, s: str):
        if s != self.state:
            self.state = s
            self.frame = 0
            self.timer = 0.0

    def _animate(self, dt: float):
        frames = self.anim[self.state]
        if len(frames) == 1:
            return
        self.timer += dt
        step = 1.0 / ANIM_FPS
        while self.timer >= step:
            self.timer -= step
            self.frame = (self.frame + 1) % len(frames)

    def _move_towards(self, target: pygame.Vector2, solids: List[pygame.Rect], dt: float):
        vec = target - pygame.Vector2(self.hitbox.center)
        if vec.length_squared() > 0:
            vec.scale_to_length(self.speed * dt)
        # axis separated collision
        self.hitbox.x += int(vec.x)
        for s in solids:
            if self.hitbox.colliderect(s):
                if vec.x > 0:
                    self.hitbox.right = s.left
                elif vec.x < 0:
                    self.hitbox.left = s.right
        self.hitbox.y += int(vec.y)
        for s in solids:
            if self.hitbox.colliderect(s):
                if vec.y > 0:
                    self.hitbox.bottom = s.top
                elif vec.y < 0:
                    self.hitbox.top = s.bottom
        self.rect.center = self.hitbox.center

    # ------------------------------------------------------------------
    def update(self, dt: float, room, player):
        if not self.alive:
            return
        if self._attack_cd > 0:
            self._attack_cd -= dt

        player_center = pygame.Vector2(player.hitbox.center)
        to_player = player_center - pygame.Vector2(self.hitbox.center)
        dist = to_player.length()

        if self.state == "attack":
            # Attempt damage on hit frame
            if not self._did_hit_this_attack and self.frame == self.attack_hit_frame:
                if dist <= self.attack_radius + 4:
                    if hasattr(player, "take_damage"):
                        player.take_damage(self.attack_damage)
                    if hasattr(player, "hurt_from"):
                        player.hurt_from(self.hitbox.center)
                    self._did_hit_this_attack = True
        else:
            if dist <= self.attack_radius and self._attack_cd <= 0:
                self._set_state("attack")
                self._did_hit_this_attack = False
                self._attack_time = self.attack_anim_length
            elif dist <= self.notice_radius:
                self._set_state("move")
                self._move_towards(player_center, room.solid_rects(), dt)
            else:
                self._set_state("idle")

        prev_frame = self.frame
        # animate
        self._animate(dt)

        if self.state == "attack":
            # single-frame fallback timer
            self._attack_time = max(0.0, self._attack_time - dt)
            atk_len = len(self.anim.get("attack", []))
            if prev_frame > self.frame or (atk_len <= 1 and self._attack_time <= 0):
                # attack cycle finished
                self._set_state("idle")
                self._attack_cd = self.attack_cooldown
                self._did_hit_this_attack = False

        # keep sprite rect aligned to hitbox feet
        self.rect.midbottom = (self.hitbox.centerx, self.hitbox.bottom - self.offset_y)

    # ------------------------------------------------------------------
    def draw(self, screen: pygame.Surface, offset: Tuple[int, int]):
        if not self.alive:
            return
        frames = self.anim[self.state]
        img = frames[self.frame % len(frames)]
        screen.blit(img, self.rect.move(offset))

    def is_dead(self) -> bool:
        return (not self.alive) or (self.hp <= 0)

    def take_damage(self, amount: int):
        amount = max(0, int(amount))
        if amount <= 0 or not self.alive:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False
