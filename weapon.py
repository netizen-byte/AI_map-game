import pygame
from typing import Tuple

class Weapon(pygame.sprite.Sprite):
    _cache: dict[str, pygame.Surface] = {}
    def __init__(self, player, groups):
        """
        Initializes the weapon and determines its position based on the player's facing direction.
        The weapon will be held by the player when the attack is triggered.
        """
        super().__init__(groups)
        self.player = player
        self.sprite_type = 'weapon'
        self.direction = player.facing
        self._base_name = 'full'  # optional base sprite name
        self._load_image()
        self._position()

    def _load_raw(self, name: str) -> pygame.Surface | None:
        for p in (f"weapons/{name}.png", f"weapons/sword/{name}.png"):
            try:
                return pygame.image.load(p).convert_alpha()
            except Exception:
                continue
        return None

    def _load_image(self):
        key = self.direction
        if key in self._cache:
            self.image = self._cache[key]
            return
        raw = self._load_raw(self.direction) or self._load_raw(self._base_name)
        if raw is None:
            raw = pygame.Surface((24, 44), pygame.SRCALPHA)
            pygame.draw.rect(raw, (255,0,0), raw.get_rect(), 2)
        # rotate if needed
        if self.direction in ('left','right') and raw.get_height() > raw.get_width():
            angle = -90 if self.direction=='right' else 90
            raw = pygame.transform.rotate(raw, angle)
        # --- scale down for nicer proportion ---
        SCALE = 0.68  # slightly larger than before
        w, h = raw.get_size()
        scaled_size = (max(1, int(w * SCALE)), max(1, int(h * SCALE)))
        img = pygame.transform.smoothscale(raw, scaled_size)
        self.image = img
        self._cache[key] = img
        print(f"Weapon loaded (dir={self.direction}) size={self.image.get_width()}x{self.image.get_height()} (src {w}x{h})")

    def _position(self):
        p = self.player.rect
        # outward distance from player body
        OUT = -5   # reduced gap so sword is closer to body
        UP_SHIFT = -2  # minor vertical tweak
        if self.direction == 'right':
            self.rect = self.image.get_rect(midleft=p.midright + pygame.Vector2(OUT, UP_SHIFT))
        elif self.direction == 'left':
            self.rect = self.image.get_rect(midright=p.midleft + pygame.Vector2(-OUT, UP_SHIFT))
        elif self.direction == 'down':
            self.rect = self.image.get_rect(midtop=p.midbottom + pygame.Vector2(0, OUT * 0.6))
        else:  # up
            self.rect = self.image.get_rect(midbottom=p.midtop + pygame.Vector2(0, -OUT * 0.4))

    def update(self):
        """
        Updates the weapon's position and orientation.
        This is called every frame to ensure the weapon stays attached to the player.
        """
        if self.direction != self.player.facing:
            self.direction = self.player.facing
            self._load_image()
        self._position()

    def draw(self, surface: pygame.Surface, offset: Tuple[int,int]):
        r = self.rect.move(offset)
        surface.blit(self.image, r)
    # Removed yellow debug outline box.
        if not hasattr(self, '_debug_once'):
            print(f"Draw sword at {r.topleft} size={self.image.get_size()}")
            self._debug_once = True
