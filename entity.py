# entity.py
import pygame
from math import sin

class Entity(pygame.sprite.Sprite):
    def __init__(self, groups, obstacle_sprites):
        super().__init__(groups)
        self.frame_index = 0
        self.animation_speed = 0.15
        self.direction = pygame.math.Vector2()
        self.obstacle_sprites = obstacle_sprites

    def move(self, speed):
        if self.direction.length_squared() != 0:
            self.direction = self.direction.normalize()

        # X
        self.hitbox.x += self.direction.x * speed
        self._collision('horizontal')

        # Y
        self.hitbox.y += self.direction.y * speed
        self._collision('vertical')

        self.rect.center = self.hitbox.center

    def _collision(self, direction):
        for sprite in self.obstacle_sprites:
            if sprite.hitbox.colliderect(self.hitbox):
                if direction == 'horizontal':
                    if self.direction.x > 0:   self.hitbox.right = sprite.hitbox.left
                    if self.direction.x < 0:   self.hitbox.left  = sprite.hitbox.right
                else:
                    if self.direction.y > 0:   self.hitbox.bottom = sprite.hitbox.top
                    if self.direction.y < 0:   self.hitbox.top    = sprite.hitbox.bottom

    def wave_value(self):
        return 255 if sin(pygame.time.get_ticks()) >= 0 else 0
