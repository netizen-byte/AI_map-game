# boss.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import pygame

from constants import TILE
try:
    from constants import ANIM_FPS
except Exception:
    ANIM_FPS = 8

def _load_strip(folder: Path, out_wh: Tuple[int,int]) -> List[pygame.Surface]:
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
    """Raccoon boss that chases and contact-hurts the player."""
    def __init__(self, pos: Tuple[int,int], tile_size: int = TILE):
        self.size_tiles = 2
        self.w = self.h = self.size_tiles * tile_size
        self.offset_y = -int(0.25 * tile_size)

        base = Path("monsters") / "raccoon"
        self.anim: Dict[str, List[pygame.Surface]] = {
            "idle":   _load_strip(base / "idle",   (self.w, self.h)),
            "move":   _load_strip(base / "move",   (self.w, self.h)),
            "attack": _load_strip(base / "attack", (self.w, self.h)),
        }
        # Fallback if folders are empty
        if not self.anim["idle"]:
            dummy = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            pygame.draw.circle(dummy, (240,180,50,220), (self.w//2, self.h//2), self.w//2)
            self.anim["idle"] = [dummy]
            self.anim["move"] = [dummy]
            self.anim["attack"] = [dummy]

        self.state = "idle"
        self.frame = 0
        self.timer = 0.0

        self.pos = pygame.Vector2(pos)
        self.rect = pygame.Rect(0, 0, self.w, self.h)
        self.rect.midbottom = (int(self.pos.x), int(self.pos.y) + self.offset_y)
        self.hitbox = self.rect.inflate(-self.w//4, -self.h//4)

        self.max_hp = 20
        self.hp = self.max_hp
        self.speed = 90.0
        self.notice_radius = 3 * tile_size
        self.attack_radius = 1 * tile_size
        self.touch_damage = 1
        self.attack_cooldown = 0.8
        self._attack_cd = 0.0

        self.alive = True

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
        dir = target - pygame.Vector2(self.hitbox.center)
        if dir.length_squared() > 0:
            dir.scale_to_length(self.speed * dt)
        # axis-separated collision
        self.hitbox.x += int(dir.x)
        for s in solids:
            if self.hitbox.colliderect(s):
                if dir.x > 0: self.hitbox.right = s.left
                elif dir.x < 0: self.hitbox.left = s.right
        self.hitbox.y += int(dir.y)
        for s in solids:
            if self.hitbox.colliderect(s):
                if dir.y > 0: self.hitbox.bottom = s.top
                elif dir.y < 0: self.hitbox.top = s.bottom
        self.rect.center = self.hitbox.center

    def update(self, dt: float, room, player):
        if not self.alive:
            return
        if self._attack_cd > 0:
            self._attack_cd -= dt

        player_center = pygame.Vector2(player.hitbox.center)
        to_player = player_center - pygame.Vector2(self.hitbox.center)
        dist = to_player.length()

        if dist <= self.attack_radius and self._attack_cd <= 0:
            self._set_state("attack")
            if hasattr(player, "take_damage"):
                player.take_damage(self.touch_damage)
            if hasattr(player, "hurt_from"):
                player.hurt_from(self.hitbox.center)
            self._attack_cd = self.attack_cooldown
        elif dist <= self.notice_radius:
            self._set_state("move")
            self._move_towards(player_center, room.solid_rects(), dt)
        else:
            self._set_state("idle")

        self.rect = pygame.Rect(0, 0, self.w, self.h)
        self.rect.midbottom = (self.hitbox.centerx, self.hitbox.bottom - self.offset_y)
        self._animate(dt)

    def draw(self, screen: pygame.Surface, offset: Tuple[int,int]):
        if not self.alive:
            return
        frames = self.anim[self.state]
        img = frames[self.frame % len(frames)]
        screen.blit(img, self.rect.move(offset))

    def is_dead(self) -> bool:
        return (not self.alive) or (self.hp <= 0)

    def take_damage(self, amount: int):
        self.hp -= max(0, int(amount))
        if self.hp <= 0:
            self.alive = False
