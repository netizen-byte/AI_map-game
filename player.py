# player.py
import pygame
from constants import *
from sprite_loader import sprite_loader

class Player:
    def __init__(self, x: int, y: int):
        # collision box (sprite centered over this)
        self.width = 20
        self.height = 20
        self.rect = pygame.Rect(int(x), int(y), self.width, self.height)
        self.speed = 140.0

        # stats / hurt logic
        self.hp = PLAYER_MAX_HP
        self.stamina = PLAYER_MAX_STAMINA
        self.iframes = 0.0
        self.kb_dx = 0.0
        self.kb_dy = 0.0
        self.kb_time = 0.0

        # animation
        self.animations = sprite_loader.load_player_animations()
        self.dir = "down"
        self.state = "idle"   # "idle", "walk", "attack", "hit"
        self.frame = 0
        self.timer = 0.0

    # --- input events (edge-trigger attack) ---
    def handle_event(self, e: pygame.event.Event):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_j):
            if self.state != "attack" and self.stamina >= STAMINA_COST_ATTACK and self.state != "hit":
                self.state = "attack"
                self.frame = 0
                self.timer = 0.0
                self.stamina -= STAMINA_COST_ATTACK

    def _axis_input(self) -> tuple[float, float]:
        keys = pygame.key.get_pressed()
        vx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT])
        vy = float(keys[pygame.K_s] or keys[pygame.K_DOWN])  - float(keys[pygame.K_w] or keys[pygame.K_UP])
        if vx and vy:
            inv = 0.70710678
            vx *= inv; vy *= inv
        return vx, vy

    def attack_hitbox(self) -> pygame.Rect | None:
        if self.state != "attack":
            return None
        frames = self.animations.get(f"attack_{self.dir}")
        if not frames:
            return None
        active = (self.frame >= 1) and (self.frame <= max(1, len(frames)-2))
        if not active:
            return None
        r = self.rect; reach = 18; w = h = 18
        if self.dir == "up":    return pygame.Rect(r.centerx - w//2, r.top - reach, w, h)
        if self.dir == "down":  return pygame.Rect(r.centerx - w//2, r.bottom, w, h)
        if self.dir == "left":  return pygame.Rect(r.left - reach, r.centery - h//2, w, h)
        if self.dir == "right": return pygame.Rect(r.right, r.centery - h//2, w, h)

    def take_damage(self, dmg: int, source_pos: tuple[int,int] | None = None):
        if self.iframes > 0:
            return
        self.hp = max(0, self.hp - dmg)
        # enter hurt state + i-frames
        self.state = "hit"
        self.frame = 0
        self.timer = 0.0
        self.iframes = IFRAME_TIME
        # compute knockback away from source
        if source_pos:
            sx, sy = source_pos
            dx = self.rect.centerx - sx
            dy = self.rect.centery - sy
        else:
            dx, dy = 0.0, 1.0  # fall-back
        # normalize
        mag = (dx*dx + dy*dy) ** 0.5 or 1.0
        self.kb_dx = (dx / mag) * HIT_KNOCKBACK_SPEED
        self.kb_dy = (dy / mag) * HIT_KNOCKBACK_SPEED
        self.kb_time = HIT_KNOCKBACK_TIME

    def update(self, dt: float, room, solid_rects=()):
        # timers/stamina
        if self.iframes > 0: self.iframes -= dt
        if self.state != "attack" and self.state != "hit":
            self.stamina = min(PLAYER_MAX_STAMINA, self.stamina + STAMINA_REGEN_PER_SEC * dt)

        vx, vy = self._axis_input()

        # facing (locked while hit/attack so anim matches)
        if self.state not in ("attack", "hit"):
            if abs(vx) > abs(vy) and vx != 0:
                self.dir = "right" if vx > 0 else "left"
            elif vy != 0:
                self.dir = "down" if vy > 0 else "up"

        # movement:
        #  - if 'hit': you CAN move (on top of decaying knockback), enemies won't block during i-frames
        #  - if 'attack': movement disabled (classic feel)
        mvx = mvy = 0
        if self.state != "attack":
            mvx = int(round(vx * self.speed * dt))
            mvy = int(round(vy * self.speed * dt))

        # apply knockback (decays)
        if self.kb_time > 0:
            k = max(0.0, self.kb_time / HIT_KNOCKBACK_TIME)
            mvx += int(round(self.kb_dx * k * dt))
            mvy += int(round(self.kb_dy * k * dt))
            self.kb_time -= dt

        # X then Y against walls
        self.rect.x += mvx
        if room.rect_collides(self.rect):
            self.rect.x -= mvx
        self.rect.y += mvy
        if room.rect_collides(self.rect):
            self.rect.y -= mvy

        if self.state not in ("attack", "hit"):
            self.state = "walk" if (vx or vy) else "idle"

        # animation advance
        key = f"{self.state}_{self.dir}"
        frames = self.animations.get(key, self.animations.get(f"idle_{self.dir}"))
        if not frames:
            frames = self.animations[f"idle_{self.dir}"]

        self.timer += dt
        if self.timer >= 1.0 / ANIMATION_FPS:
            self.timer = 0.0
            self.frame += 1
            if self.frame >= len(frames):
                if self.state == "attack":
                    self.state = "idle"
                elif self.state == "hit":
                    # after hurt anim finishes, go idle and keep any remaining i-frames
                    self.state = "idle"
                self.frame = 0

    def render(self, surface: pygame.Surface):
        key = f"{self.state}_{self.dir}"
        frames = self.animations.get(key, self.animations.get(f"idle_{self.dir}"))
        sprite = frames[self.frame]
        dest = sprite.get_rect(); dest.center = self.rect.center
        surface.blit(sprite, dest)
        # Debug: draw i-frame outline
        # if self.iframes > 0: pygame.draw.rect(surface, (255,255,0), self.rect, 1)
