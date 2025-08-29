from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import pygame

from constants import TILE, ANIM_FPS, PLAYER_SPEED, PLAYER_MAX_HP

# -------- helpers to robustly find your sprite sheets ----------
def _load_first_existing(paths: List[str]) -> pygame.Surface:
    """Try multiple relative paths; also fallback to sprites/ folder."""
    for p in paths:
        cand = Path(p)
        if cand.exists():
            return pygame.image.load(cand.as_posix()).convert_alpha()
        alt = Path("sprites") / cand.name
        if alt.exists():
            return pygame.image.load(alt.as_posix()).convert_alpha()
    raise FileNotFoundError(f"None of these images exist: {paths}")

def _slice_strip(sheet: pygame.Surface) -> List[pygame.Surface]:
    h = sheet.get_height()
    frame = min(h, TILE)           # your frames are 32×32
    count = max(1, sheet.get_width() // frame)
    return [sheet.subsurface(pygame.Rect(i*frame, 0, frame, frame)).copy()
            for i in range(count)] or [sheet]
# ---------------------------------------------------------------

class Player:
    def __init__(self, spawn_xy: Tuple[int,int]) -> None:
        candidates: Dict[str, List[str]] = {
            "idle_down":  ["sprites/Staystill.png", "sprites/Walk_forward.png"],
            "idle_up":    ["sprites/Stay_still_back.png", "sprites/Walk_up.png"],
            "idle_left":  ["sprites/Stay_still_left.png", "sprites/Stay_still_left_.png", "sprites/Walk_left.png"],
            "idle_right": ["sprites/Stay_still_right.png", "sprites/Walk_right.png"],
            "walk_down":  ["sprites/Walk_forward.png"],
            "walk_up":    ["sprites/Walk_up.png"],
            "walk_left":  ["sprites/Walk_left.png"],
            "walk_right": ["sprites/Walk_right.png"],
        }
        self.anim: Dict[str, List[pygame.Surface]] = {}
        for k, opts in candidates.items():
            self.anim[k] = _slice_strip(_load_first_existing(opts))

        self.facing = "down"
        self.state  = "idle_down"
        self.frame  = 0
        self.timer  = 0.0
        self.image  = self.anim[self.state][self.frame]
        self.rect   = self.image.get_rect(center=spawn_xy)
        # smaller hitbox used for hazard checks (not movement)
        self.hitbox = self.rect.inflate(-8, -8)
        self.vel    = pygame.Vector2(0, 0)
        # health
        self.max_hp = PLAYER_MAX_HP
        self.hp = PLAYER_MAX_HP
        self.invuln_timer = 0.0  # used for brief hit flash if desired
        self.hurt_timer = 0.0
        self.dead = False

        if Path("sprites/Hurt.png").exists():
            self.anim["hurt"] = _slice_strip(pygame.image.load("sprites/Hurt.png").convert_alpha())

        # optional extra animations
        if Path("sprites/Die.png").exists():
            self.anim["dead"] = _slice_strip(pygame.image.load("sprites/Die.png").convert_alpha())
        # fallback hurt animation uses idle frame flash (no extra art needed)
        
    def set_state(self, name: str) -> None:
        """Force an animation immediately (used on room enter)."""
        if name in self.anim:
            self.state, self.facing, self.frame, self.timer = name, name.split("_")[-1], 0, 0.0
            self.image = self.anim[name][0]


    def teleport(self, xy: Tuple[int,int]) -> None:
        self.rect.center = xy

    def _read_input(self) -> None:
        k = pygame.key.get_pressed()
        if self.hurt_timer > 0 or self.dead:
            return
        vx = (1 if (k[pygame.K_d] or k[pygame.K_RIGHT]) else 0) - (1 if (k[pygame.K_a] or k[pygame.K_LEFT]) else 0)
        vy = (1 if (k[pygame.K_s] or k[pygame.K_DOWN]) else 0) - (1 if (k[pygame.K_w] or k[pygame.K_UP]) else 0)
        self.vel.update(vx, vy)
        if self.vel.length_squared() > 0:
            self.vel = self.vel.normalize() * PLAYER_SPEED
            if abs(self.vel.x) > abs(self.vel.y):
                self.facing = "right" if self.vel.x > 0 else "left"
            else:
                self.facing = "down" if self.vel.y > 0 else "up"

    def _set_anim(self, moving: bool) -> None:
        if self.dead:
            wanted = "dead" if "dead" in self.anim else f"idle_{self.facing}"
        elif self.hurt_timer > 0:
            wanted = "hurt" if "hurt" in self.anim else f"idle_{self.facing}"
        else:
            wanted = f"{'walk' if moving else 'idle'}_{self.facing}"
        if wanted != self.state:
            self.state, self.frame, self.timer = wanted, 0, 0.0

    def _animate(self, dt: float) -> None:
        frames = self.anim[self.state]
        if len(frames) == 1:
            self.image = frames[0]; return
        self.timer += dt
        step = 1.0 / ANIM_FPS
        while self.timer >= step:
            self.timer -= step
            self.frame = (self.frame + 1) % len(frames)
        self.image = frames[self.frame]

    def _move_axis(self, dx: float, dy: float, solids: List[pygame.Rect]) -> None:
        if dx:
            self.rect.x += int(dx)
            for s in solids:
                if self.rect.colliderect(s):
                    self.rect.right = min(self.rect.right, s.left) if dx > 0 else self.rect.right
                    self.rect.left  = max(self.rect.left,  s.right) if dx < 0 else self.rect.left
        if dy:
            self.rect.y += int(dy)
            for s in solids:
                if self.rect.colliderect(s):
                    self.rect.bottom = min(self.rect.bottom, s.top) if dy > 0 else self.rect.bottom
                    self.rect.top    = max(self.rect.top,    s.bottom) if dy < 0 else self.rect.top

    # offset = camera/room offset; update works with world solids shifted to screen
    def update(self, dt: float, room, offset: Tuple[int,int]=(0,0)) -> None:
        self._read_input()
        moving = self.vel.length_squared() > 0
        self._set_anim(moving)

        if moving and not self.dead:
            solids = room.solid_rects(offset)
            self._move_axis(self.vel.x * dt, 0, solids)
            self._move_axis(0, self.vel.y * dt, solids)

        self._animate(dt)
        if self.invuln_timer > 0:
            self.invuln_timer = max(0.0, self.invuln_timer - dt)
        if self.hurt_timer > 0:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)
            # apply knockback decay
            self.rect.x += int(self.vel.x * dt)
            self.rect.y += int(self.vel.y * dt)
            self.vel *= 0.88
        # keep hitbox centered on rect
        self.hitbox.center = self.rect.center

    def heal_full(self) -> None:
        self.hp = self.max_hp

    def take_damage(self, amount: int) -> None:
        if amount <= 0:
            return
        self.hp = max(0, self.hp - amount)
        self.invuln_timer = 0.2

    def hurt_from(self, source_pos, knockback: float=None, duration: float=0.18) -> None:
        if self.dead: return
        sx, sy = source_pos
        v = pygame.Vector2(self.rect.centerx - sx, self.rect.centery - sy)
        v = pygame.Vector2(0, 1) if v.length_squared()==0 else v.normalize()
        if knockback is None:
            knockback = TILE / max(1e-3, duration)
        self.vel = v * knockback
        self.hurt_timer = duration

    def kill_instant(self) -> None:
        self.hp = 0
        self.dead = True
        self.state = "dead" if "dead" in self.anim else self.state
        self.frame = 0
        self.timer = 0.0
