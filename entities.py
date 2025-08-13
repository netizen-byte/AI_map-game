# entities.py
import pygame
from math import hypot
from constants import *

class Enemy:
    def __init__(self, x: int, y: int):
        self.rect = pygame.Rect(int(x), int(y), 20, 20)
        self.speed = 80.0
        self.max_hp = ENEMY_MAX_HP
        self.hp = self.max_hp
        self.alive = True

    def update(self, dt: float, room, player):
        if not self.alive:
            return

        # chase player
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        d = hypot(dx, dy) or 1.0
        vx, vy = dx/d, dy/d

        mx = int(round(vx * self.speed * dt))
        my = int(round(vy * self.speed * dt))

        # move vs walls
        self.rect.x += mx
        if room.rect_collides(self.rect):
            self.rect.x -= mx
        self.rect.y += my
        if room.rect_collides(self.rect):
            self.rect.y -= my

        # contact damage (player handles i-frames internally)
        if self.rect.colliderect(player.rect):
            player.take_damage(ENEMY_CONTACT_DAMAGE, self.rect.center)

        # hit by player's attack?
        hb = player.attack_hitbox()
        if hb and hb.colliderect(self.rect):
            self.hp -= 1
            if self.hp <= 0:
                self.alive = False

    def render(self, surf: pygame.Surface):
        if not self.alive:
            return
        # body
        pygame.draw.rect(surf, (200, 70, 70), self.rect)
        # HP bar
        bw, bh = 24, 4
        bx = self.rect.centerx - bw // 2
        by = self.rect.top - 8
        pygame.draw.rect(surf, (30,30,40), (bx-1, by-1, bw+2, bh+2))
        fill = int(bw * (self.hp / self.max_hp))
        pygame.draw.rect(surf, (230,80,80), (bx, by, fill, bh))
