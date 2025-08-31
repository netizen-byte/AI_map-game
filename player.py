from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import pygame
from weapon import Weapon  # Import Weapon class

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
            "attack_down":  ["sprites/Staystill.png"],  # Placeholder
            "attack_up":    ["sprites/Stay_still_back.png"],  # Placeholder
            "attack_left":  ["sprites/Stay_still_left.png"],  # Placeholder
            "attack_right": ["sprites/Stay_still_right.png"]  # Placeholder
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

        # --- REDUCED HITBOX ---
        # Adjust hitbox to be just around the player character
        hb = self.rect.copy()
        hb.width = int(hb.width * 0.8)  # ~80% of sprite width
        hb.height = int(hb.height * 0.8)  # ~80% of sprite height
        hb.center = self.rect.center  # Align with player center
        self.hitbox = hb

        self.vel    = pygame.Vector2(0, 0)
        # health
        self.max_hp = PLAYER_MAX_HP
        self.hp = PLAYER_MAX_HP
        self.invuln_timer = 0.0
        self.hurt_timer = 0.0
        self.dead = False

        # Ensure knock attribute exists in Player class
        self.knock = pygame.Vector2(0, 0)  # transient knockback velocity

        # Attack system
        self.attacking = False  # To track if the player is attacking
        self.attack_timer = 0  # Attack cooldown timer
        self.weapon = None  # Hold weapon (sword)
        self.attack_duration = 0.3  # Attack lasts for 0.3 seconds

        if Path("sprites/Hurt.png").exists():
            self.anim["hurt"] = _slice_strip(pygame.image.load("sprites/Hurt.png").convert_alpha())

        if Path("sprites/Die.png").exists():
            self.anim["dead"] = _slice_strip(pygame.image.load("sprites/Die.png").convert_alpha())
        
    def set_state(self, name: str) -> None:
        """Force an animation immediately (used on room enter)."""
        if name in self.anim:
            self.state, self.facing, self.frame, self.timer = name, name.split("_")[-1], 0, 0.0
            self.image = self.anim[name][0]

    def teleport(self, xy: Tuple[int,int]) -> None:
        self.rect.center = xy
        # keep feet hitbox glued to feet after teleports
        self.hitbox.midbottom = self.rect.midbottom

    def _read_input(self) -> None:
        k = pygame.key.get_pressed()
        if self.hurt_timer > 0 or self.dead:
            # Suppress player-controlled movement while hurt/dead, but keep knockback
            self.vel.update(0, 0)
            return
        
        vx = (1 if (k[pygame.K_d] or k[pygame.K_RIGHT]) else 0) - (1 if (k[pygame.K_a] or k[pygame.K_LEFT]) else 0)
        vy = (1 if (k[pygame.K_s] or k[pygame.K_DOWN]) else 0) - (1 if (k[pygame.K_w] or k[pygame.K_UP]) else 0)

        # Attack input: Spacebar
        if k[pygame.K_SPACE] and not self.attacking:
            self.attacking = True
            self.attack_timer = self.attack_duration  # Start the attack
            self.weapon = Weapon(self, groups=[])  # Create the sword/weapon

        # Player movement (if not attacking)
        if not self.attacking:
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
        elif self.attacking:
            wanted = f"attack_{self.facing}"  # Use attack animation when attacking
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
            if self.state == "dead":
                if self.frame < len(frames) - 1:
                    self.frame += 1
            elif self.state.startswith("attack"):
                if self.frame < len(frames) - 1:
                    self.frame += 1
            else:
                self.frame = (self.frame + 1) % len(frames)
        self.image = frames[self.frame]

    def _move_axis(self, dx: float, dy: float, solids: List[pygame.Rect], walkable_objects: List[pygame.Rect] = None) -> None:
        if walkable_objects is None:
            walkable_objects = []
        
        # Create a head-level collision area (top portion of player)
        head_rect = self.rect.copy()
        head_rect.height = int(self.rect.height * 0.65)  # Top 65% of player is head
        head_rect.bottom = self.rect.bottom  # Align with player bottom
        
        if dx:
            self.rect.x += int(dx)
            for s in solids:
                if self.rect.colliderect(s):
                    # Check if this is a walkable object
                    is_walkable = s in walkable_objects
                    if is_walkable:
                        # For walkable objects, only block if the head area collides
                        # If head doesn't collide, allow the player to pass through
                        if head_rect.colliderect(s):
                            # Head collides with walkable object, so block movement
                            print(f"HEAD COLLISION DETECTED with walkable object {s}")
                            self.rect.right = min(self.rect.right, s.left) if dx > 0 else self.rect.right
                            self.rect.left  = max(self.rect.left,  s.right) if dx < 0 else self.rect.left
                        else:
                            print(f"Head can pass through walkable object {s}")
                        # If head doesn't collide, do nothing (allow passage)
                    else:
                        # For solid objects, block the entire player
                        print(f"Solid object collision with {s}")
                        self.rect.right = min(self.rect.right, s.left) if dx > 0 else self.rect.right
                        self.rect.left  = max(self.rect.left,  s.right) if dx < 0 else self.rect.left
        if dy:
            self.rect.y += int(dy)
            for s in solids:
                if self.rect.colliderect(s):
                    # Check if this is a walkable object
                    is_walkable = s in walkable_objects
                    if is_walkable:
                        # For walkable objects, only block if the head area collides
                        # If head doesn't collide, allow the player to pass through
                        if head_rect.colliderect(s):
                            # Head collides with walkable object, so block movement
                            print(f"HEAD COLLISION DETECTED with walkable object {s}")
                            self.rect.bottom = min(self.rect.bottom, s.top) if dy > 0 else self.rect.bottom
                            self.rect.top    = max(self.rect.top,    s.bottom) if dy < 0 else self.rect.top
                        else:
                            print(f"Head can pass through walkable object {s}")
                        # If head doesn't collide, do nothing (allow passage)
                    else:
                        # For solid objects, block the entire player
                        print(f"Solid object collision with {s}")
                        self.rect.bottom = min(self.rect.bottom, s.top) if dy > 0 else self.rect.bottom
                        self.rect.top    = max(self.rect.top,    s.bottom) if dy < 0 else self.rect.top

    # offset = camera/room offset; update works with world solids shifted to screen
    def update(self, dt: float, room, offset: Tuple[int,int]=(0,0)) -> None:
        self._read_input()
        # moving flag counts either input velocity (when allowed) or active knockback
        moving = (self.vel.length_squared() > 0 and not self.attacking) or (self.knock.length_squared() > 6 and self.hurt_timer > 0)
        self._set_anim(moving)

        if self.attacking:
            self.attack_timer -= dt  # Countdown to end attack
            if self.weapon:
                self.weapon.update()
            if self.attack_timer <= 0:
                self.attacking = False  # End the attack
                self.weapon = None

        solids = room.solid_rects(offset)
        walkable_objects = room.walkable_rects(offset)
        
        # DEBUG: Print collision info
        print(f"Solids count: {len(solids)}")
        print(f"Walkable objects count: {len(walkable_objects)}")
        if walkable_objects:
            print(f"First walkable object: {walkable_objects[0]}")
        if solids:
            print(f"First solid: {solids[0]}")
        # Apply player input movement (blocked while attacking or dead)
        if not self.dead and not self.attacking and self.vel.length_squared() > 0:
            self._move_axis(self.vel.x * dt, 0, solids, walkable_objects)
            self._move_axis(0, self.vel.y * dt, solids, walkable_objects)

        # Apply knockback while hurt
        if self.hurt_timer > 0 and self.knock.length_squared() > 0:
            self._move_axis(self.knock.x * dt, 0, solids, walkable_objects)
            self._move_axis(0, self.knock.y * dt, solids, walkable_objects)
            self.knock *= 0.88
            if self.knock.length_squared() < 4:
                self.knock.update(0, 0)

        self._animate(dt)
        if self.invuln_timer > 0:
            self.invuln_timer = max(0.0, self.invuln_timer - dt)
        if self.hurt_timer > 0:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)

        # keep the smaller "feet" hitbox glued to the feet every frame
        self.hitbox.midbottom = self.rect.midbottom

    def heal_full(self) -> None:
        self.hp = self.max_hp

    def take_damage(self, amount: int) -> None:
        if amount <= 0:
            return
        self.hp = max(0, self.hp - amount)
        self.invuln_timer = 0.2
        # Play the hit sound every time the player takes damage
        hit_sound.play()

    def hurt_from(self, source_pos, knockback: float=None, duration: float=0.18) -> None:
        if self.dead: return
        sx, sy = source_pos
        v = pygame.Vector2(self.rect.centerx - sx, self.rect.centery - sy)
        v = pygame.Vector2(0, 1) if v.length_squared()==0 else v.normalize()
        if knockback is None:
            knockback = TILE / max(1e-3, duration)
        # store knockback separately so input doesn't cancel it
        self.knock = v * knockback
        self.hurt_timer = duration

    def draw(self, screen: pygame.Surface, off: Tuple[int,int]):
        """Draw the player and weapon (if attacking). Sword appears in front except when facing up."""
        if self.attacking and self.weapon:
            # Update weapon position just before drawing
            self.weapon.update()
            if self.facing == 'up':
                # sword behind player
                self.weapon.draw(screen, off)
                screen.blit(self.image, self.rect.move(off))
                return
            else:
                # sword in front of player
                screen.blit(self.image, self.rect.move(off))
                self.weapon.draw(screen, off)
                return
        # default (no attack)
        screen.blit(self.image, self.rect.move(off))
        
        # Remove hitbox visualization (yellow box)
        # Previously used for debugging; no longer needed

    def kill_instant(self) -> None:
        self.hp = 0
        self.dead = True
        self.invuln_timer = 0.0
        self.hurt_timer   = 0.0
        self.vel.update(0, 0)
        self.knock.update(0, 0)
        if "dead" in self.anim:
            self.state = "dead"
        self.frame = 0
        self.timer = 0.0

        # Play death sound when player dies
        death_sound.play()

# Initialize the mixer
pygame.mixer.init()

# Load hit sound at the top of player.py (near other imports)
hit_sound = pygame.mixer.Sound('audio/hit.wav')
hit_sound.set_volume(0.5)  # Adjust volume if necessary

# Load death sound at the top of player.py (near other imports)
death_sound = pygame.mixer.Sound('audio/death.wav')
death_sound.set_volume(0.5)  # Adjust volume if necessary
